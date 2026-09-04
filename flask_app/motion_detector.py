import cv2

class MotionDetector:
    def __init__(self):
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2()

    def detect(self, frame):
        """
        Applies background subtraction to detect motion.
        Returns the motion mask or annotated frame.
        """
        mask = self.bg_subtractor.apply(frame)
        # Add additional filtering or bounding box logic here
        return mask
