declare module "qrcode.react" {
  import * as React from "react";
  export const QRCode: React.FC<{
    value: string;
    size?: number;
    level?: "L" | "M" | "Q" | "H";
    includeMargin?: boolean;
    bgColor?: string;
    fgColor?: string;
  }>;
}
