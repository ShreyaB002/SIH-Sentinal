"""
reid_model.py ? PyTorch Implementation of Omni-Scale Network (OSNet) for Person Re-ID.

Reference:
    Zhou et al. "Omni-Scale Feature Learning for Person Re-Identification", ICCV 2019.
    https://arxiv.org/abs/1905.00953
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class Conv1x1(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, stride: int = 1, bias: bool = False):
        super().__init__()
        self.conv = nn.Conv2d(in_channels, out_channels, 1, stride=stride, padding=0, bias=bias)
        self.bn = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x):
        return self.relu(self.bn(self.conv(x)))


class Conv3x3(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, stride: int = 1, bias: bool = False):
        super().__init__()
        self.conv = nn.Conv2d(in_channels, out_channels, 3, stride=stride, padding=1, bias=bias)
        self.bn = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x):
        return self.relu(self.bn(self.conv(x)))


class LightConv3x3(nn.Module):
    """Lite 3x3 conv using depthwise-separable convolution."""
    def __init__(self, in_channels: int, out_channels: int, bias: bool = False):
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels, in_channels, 3, stride=1, padding=1, groups=in_channels, bias=bias)
        self.conv2 = nn.Conv2d(in_channels, out_channels, 1, stride=1, padding=0, bias=bias)
        self.bn = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x):
        return self.relu(self.bn(self.conv2(self.conv1(x))))


class ChannelGate(nn.Module):
    """Channel attention gate for dynamic multi-scale stream fusion."""
    def __init__(self, in_channels: int, num_gates: int = 4, reduction: int = 16):
        super().__init__()
        mid_channels = max(1, in_channels // reduction)
        self.fc1 = nn.Linear(in_channels, mid_channels)
        self.fc2 = nn.Linear(mid_channels, in_channels * num_gates)
        self.num_gates = num_gates
        self.in_channels = in_channels

    def forward(self, x):
        # Global average pool
        b, c, _, _ = x.shape
        w = F.adaptive_avg_pool2d(x, 1).view(b, c)
        w = F.relu(self.fc1(w), inplace=True)
        w = self.fc2(w).view(b, self.num_gates, self.in_channels, 1, 1)
        return torch.sigmoid(w)


class OSBlock(nn.Module):
    """Omni-scale residual block combining multi-granularity streams."""
    def __init__(self, in_channels: int, out_channels: int, bottleneck_reduction: int = 4):
        super().__init__()
        mid_channels = out_channels // bottleneck_reduction
        self.conv1 = Conv1x1(in_channels, mid_channels)

        # 4 distinct receptive field streams
        self.stream1 = LightConv3x3(mid_channels, mid_channels)
        self.stream2 = nn.Sequential(
            LightConv3x3(mid_channels, mid_channels),
            LightConv3x3(mid_channels, mid_channels),
        )
        self.stream3 = nn.Sequential(
            LightConv3x3(mid_channels, mid_channels),
            LightConv3x3(mid_channels, mid_channels),
            LightConv3x3(mid_channels, mid_channels),
        )
        self.stream4 = nn.Sequential(
            LightConv3x3(mid_channels, mid_channels),
            LightConv3x3(mid_channels, mid_channels),
            LightConv3x3(mid_channels, mid_channels),
            LightConv3x3(mid_channels, mid_channels),
        )

        self.gate = ChannelGate(mid_channels, num_gates=4)
        self.conv2 = Conv1x1(mid_channels, out_channels)

        self.downsample = None
        if in_channels != out_channels:
            self.downsample = Conv1x1(in_channels, out_channels)

    def forward(self, x):
        residual = x
        x1 = self.conv1(x)

        s1 = self.stream1(x1)
        s2 = self.stream2(x1)
        s3 = self.stream3(x1)
        s4 = self.stream4(x1)

        # Dynamic channel-wise gating fusion
        stacked = torch.stack([s1, s2, s3, s4], dim=1)  # (B, 4, C, H, W)
        weights = self.gate(x1)                         # (B, 4, C, 1, 1)
        fused = (stacked * weights).sum(dim=1)          # (B, C, H, W)

        out = self.conv2(fused)
        if self.downsample is not None:
            residual = self.downsample(residual)
        return F.relu(out + residual, inplace=True)


class OSNet(nn.Module):
    """OSNet Person Re-Identification Feature Extractor (512-d Embedding)."""
    def __init__(self, num_classes: int = 0, feature_dim: int = 512):
        super().__init__()
        self.conv1 = Conv7x7(3, 64, stride=2)
        self.maxpool = nn.MaxPool2d(3, stride=2, padding=1)

        # Layer stages
        self.layer1 = self._make_layer(64, 256, blocks=2)
        self.transition1 = Conv1x1(256, 256, stride=2)

        self.layer2 = self._make_layer(256, 384, blocks=2)
        self.transition2 = Conv1x1(384, 384, stride=2)

        self.layer3 = self._make_layer(384, 512, blocks=2)

        self.global_avgpool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Sequential(
            nn.Linear(512, feature_dim, bias=False),
            nn.BatchNorm1d(feature_dim),
        )

    def _make_layer(self, in_channels: int, out_channels: int, blocks: int):
        layers = [OSBlock(in_channels, out_channels)]
        for _ in range(1, blocks):
            layers.append(OSBlock(out_channels, out_channels))
        return nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.conv1(x)
        x = self.maxpool(x)

        x = self.layer1(x)
        x = self.transition1(x)

        x = self.layer2(x)
        x = self.transition2(x)

        x = self.layer3(x)

        x = self.global_avgpool(x)
        x = x.view(x.size(0), -1)
        features = self.fc(x)
        # Return L2-normalized 512-dimensional embedding
        return F.normalize(features, p=2, dim=1)


class Conv7x7(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, stride: int = 1):
        super().__init__()
        self.conv = nn.Conv2d(in_channels, out_channels, 7, stride=stride, padding=3, bias=False)
        self.bn = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x):
        return self.relu(self.bn(self.conv(x)))


def build_osnet(feature_dim: int = 512) -> OSNet:
    """Build and initialize OSNet feature extractor."""
    model = OSNet(feature_dim=feature_dim)
    model.eval()
    return model
