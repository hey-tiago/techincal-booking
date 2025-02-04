import { createTheme } from "@mui/material/styles";

declare module "@mui/material/styles" {
  interface Palette {
    customColors: {
      chatBubbleUser: string;
      chatBubbleSystem: string;
      textPrimary: string;
      textSecondary: string;
      borderColor: string;
      background: string;
    };
  }
  interface PaletteOptions {
    customColors: {
      chatBubbleUser: string;
      chatBubbleSystem: string;
      textPrimary: string;
      textSecondary: string;
      borderColor: string;
      background: string;
    };
  }
}

const theme = createTheme({
  palette: {
    primary: {
      main: "#0B57D0",
      dark: "#0842A0",
    },
    customColors: {
      chatBubbleUser: "#0B57D0",
      chatBubbleSystem: "#F3F4F6",
      textPrimary: "#111827",
      textSecondary: "#6B7280",
      borderColor: "#E5E7EB",
      background: "#F3F4F6",
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: "none",
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: "8px",
        },
      },
    },
  },
  shape: {
    borderRadius: 12,
  },
  typography: {
    button: {
      textTransform: "none",
    },
  },
});

export default theme;
