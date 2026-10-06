import { useEffect, useMemo, useState } from "react";
import { ConfigProvider, theme as antdTheme, App as AntApp } from "antd";
import AppShell from "./layout/AppShell.jsx";
import ErrorBoundary from "./components/ErrorBoundary.jsx";
import { BRAND, brandTokens } from "./theme/brand.js";

const THEME_KEY = "tat.theme";

export default function App() {
  const [dark, setDark] = useState(() => localStorage.getItem(THEME_KEY) === "dark");

  useEffect(() => {
    localStorage.setItem(THEME_KEY, dark ? "dark" : "light");
    document.documentElement.dataset.theme = dark ? "dark" : "light";
  }, [dark]);

  const themeConfig = useMemo(() => {
    const t = brandTokens(dark);
    return {
      algorithm: dark ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm,
      token: {
        colorPrimary: t.accent,
        colorLink: t.accent,
        colorSuccess: t.success,
        colorError: t.error,
        colorWarning: t.warning,
        colorInfo: t.info,
        borderRadius: BRAND.radiusSm,
        fontFamily: BRAND.fontBody,
        fontSize: 14,
        wireframe: false,
        // Light content canvas so white cards read as distinct panels; dark
        // mode keeps Ant's own layered surfaces.
        ...(dark ? {} : { colorBgLayout: t.surface }),
      },
      components: {
        Layout: {
          headerBg: t.bg, // ADEPT topbar: plain surface, not a colored ribbon
          headerHeight: 64,
          footerPadding: "14px 24px",
        },
        Card: { borderRadiusLG: BRAND.radiusLg, headerFontSize: 15, paddingLG: 20 },
        Table: {
          ...(dark ? {} : { headerBg: t.surface, borderColor: t.border }),
          cellPaddingBlock: 10,
        },
        Collapse: { headerPadding: "12px 16px" },
        Segmented: { borderRadius: BRAND.radiusSm },
      },
    };
  }, [dark]);

  return (
    <ConfigProvider theme={themeConfig}>
      <AntApp>
        <ErrorBoundary>
          <AppShell dark={dark} onToggleTheme={() => setDark((d) => !d)} />
        </ErrorBoundary>
      </AntApp>
    </ConfigProvider>
  );
}
