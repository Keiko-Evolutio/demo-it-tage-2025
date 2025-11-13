import {
  BrandVariants,
  createDarkTheme,
  createLightTheme,
  Theme,
} from "@fluentui/react-components";

// Define our brand colors for the theme - Keiko Brand Color #DCFF4A
const brandColors: BrandVariants = {
  10: "#0A0D02",
  20: "#1A1F05",
  30: "#2A3208",
  40: "#3A450B",
  50: "#4A580E",
  60: "#5A6B11",
  70: "#6A7E14",
  80: "#8AA51A",
  90: "#AAC820",
  100: "#CAEB26",
  110: "#D4F335",
  120: "#DCFF4A",  // Keiko Brand Color
  130: "#E3FF6F",
  140: "#E9FF8F",
  150: "#F0FFAF",
  160: "#F7FFCF",
};

export const lightTheme: Theme = {
  ...createLightTheme(brandColors),
};

export const darkTheme: Theme = {
  ...createDarkTheme(brandColors),
  colorBrandForeground1: brandColors[110],
  colorBrandForeground2: brandColors[120],
  colorBrandForegroundLink: brandColors[140],
};
