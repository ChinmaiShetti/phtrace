import "@mantine/core/styles.css";
import "@mantine/notifications/styles.css";
import "@mantine/charts/styles.css";

import "./design.css";

import { createTheme, MantineProvider } from "@mantine/core";
import { Notifications } from "@mantine/notifications";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { AuthProvider } from "./auth";

const theme = createTheme({
  primaryColor: "tide",
  colors: { tide: ["#e5faf6", "#c9f3ec", "#9ce5dc", "#6bd6ca", "#45c8bb", "#24b7aa", "#087b77", "#086c69", "#075d5b", "#094f50"] },
  fontFamily: "Inter, Segoe UI, system-ui, sans-serif",
  defaultRadius: "md",
  headings: { fontFamily: "Bahnschrift, Segoe UI, sans-serif", fontWeight: "600" },
  respectReducedMotion: true,
});

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false, staleTime: 5_000 } },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <MantineProvider theme={theme} defaultColorScheme="auto">
      <Notifications position="top-right" />
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AuthProvider>
            <App />
          </AuthProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </MantineProvider>
  </StrictMode>,
);
