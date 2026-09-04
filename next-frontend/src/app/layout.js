import { Poppins, Geist_Mono } from "next/font/google";
import "./globals.css";

const poppins = Poppins({
  variable: "--font-poppins",
  subsets: ["latin"],
  weight: [
    "400",
    "500",
    "600",
    "700",
  ],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata = {
  title: "IBVAP | Intelligent Border Video Analytics Platform",
  description:
    "Real-time intelligent video analytics, camera monitoring, object detection, tracking, and intrusion alerts.",
  applicationName: "IBVAP",
  keywords: [
    "IBVAP",
    "video analytics",
    "CCTV monitoring",
    "YOLO",
    "object detection",
    "intrusion detection",
    "camera monitoring",
  ],
};



export default function RootLayout({ children }) {
  return (
    <html
      lang="en"
      className={`${poppins.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex h-full min-h-screen bg-app-bg font-sans text-text-primary">
        <div className="flex-1 overflow-x-hidden flex flex-col h-screen">
          {children}
        </div>
      </body>
    </html>
  );
}