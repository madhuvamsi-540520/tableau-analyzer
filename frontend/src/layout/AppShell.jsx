import { Layout, Switch, Space, Typography, Grid, Tag, Tooltip, Avatar } from "antd";
import {
  ThunderboltFilled,
  BarChartOutlined,
  DatabaseOutlined,
  FunctionOutlined,
  DashboardOutlined,
  SafetyOutlined,
  SwapOutlined,
  BulbOutlined,
  BulbFilled,
  SettingOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { Routes, Route, Navigate, useNavigate, useLocation } from "react-router-dom";
import TableauAnalysis from "../pages/TableauAnalysis/index.jsx";
import DataSourceDetails from "../pages/DataSourceDetails/index.jsx";
import DaxFormula from "../pages/DaxFormula/index.jsx";
import DashboardsWorksheets from "../pages/DashboardsWorksheets/index.jsx";
import WellArchitected from "../pages/WellArchitected/index.jsx";
import MigrationAssessment from "../pages/MigrationAssessment/index.jsx";
import { BRAND, BRAND_DARK } from "../theme/brand.js";

const { Header, Content, Footer } = Layout;
const { useBreakpoint } = Grid;

const APP_NAME = "PowerShift BI Migration Studio";
const APP_VERSION = "v0.2.0";

export const TABS = [
  { key: "/tableau-analysis", label: "Tableau Analysis", icon: <BarChartOutlined /> },
  { key: "/data-source-details", label: "Data Source Details", icon: <DatabaseOutlined /> },
  { key: "/dax-formula", label: "DAX & Formula", icon: <FunctionOutlined /> },
  { key: "/dashboards-worksheets", label: "Dashboards & Worksheets", icon: <DashboardOutlined /> },
  { key: "/well-architected", label: "Well-Architected Power BI Framework", icon: <SafetyOutlined /> },
  { key: "/migration-assessment", label: "Migration Assessment", icon: <SwapOutlined /> },
];

export default function AppShell({ dark, onToggleTheme }) {
  const navigate = useNavigate();
  const location = useLocation();
  const screens = useBreakpoint();
  const selected = TABS.find((t) => location.pathname.startsWith(t.key))?.key || TABS[0].key;

  return (
    <Layout style={{ minHeight: "100vh" }}>
      {/* ADEPT topbar: plain surface + border, brand mark carries the color */}
      <Header
        style={{
          display: "flex",
          alignItems: "center",
          gap: 16,
          paddingInline: screens.md ? 24 : 12,
          height: 64,
          borderBottom: "1px solid var(--border)",
        }}
      >
        <Space size={12} style={{ flex: 1, minWidth: 0 }}>
          <div
            aria-label="logo"
            style={{
              width: 36, height: 36, borderRadius: 9, flexShrink: 0,
              display: "grid", placeItems: "center",
              background: `linear-gradient(135deg, ${BRAND.tealPrimary}, ${BRAND.green})`,
            }}
          >
            <ThunderboltFilled style={{ color: BRAND_DARK.onAccent, fontSize: 19 }} />
          </div>
          {screens.sm && (
            <Typography.Text
              strong
              style={{ color: "var(--text-primary)", fontFamily: "var(--font-head)", fontSize: 18, whiteSpace: "nowrap" }}
            >
              PowerShift <span style={{ color: "var(--text-secondary)" }}>BI Migration Studio</span>
            </Typography.Text>
          )}
          <Tag
            bordered={false}
            style={{ marginInlineStart: 4, color: "var(--text-secondary)", background: "var(--surface-alt)" }}
          >
            {APP_VERSION}
          </Tag>
        </Space>

        <Space size={screens.sm ? 14 : 8} align="center">
          <Space size={6} align="center">
            <BulbOutlined style={{ color: "var(--text-secondary)" }} />
            <Switch
              checked={dark}
              onChange={onToggleTheme}
              checkedChildren={<BulbFilled />}
              unCheckedChildren={<BulbOutlined />}
              aria-label="Toggle dark mode"
            />
          </Space>
          <Tooltip title="Settings — coming soon">
            <SettingOutlined style={{ color: "var(--text-secondary)", fontSize: 18, cursor: "not-allowed", opacity: 0.7 }} />
          </Tooltip>
          <Tooltip title="User profile — coming soon">
            <Avatar size={30} icon={<UserOutlined />} style={{ backgroundColor: "var(--surface-alt)", cursor: "not-allowed" }} />
          </Tooltip>
        </Space>
      </Header>

      {/* Navigation tabs, immediately below the header */}
      <nav className="nav-tabbar" aria-label="Primary">
        <div className="nav-tabbar__inner">
          {TABS.map((t) => {
            const active = t.key === selected;
            return (
              <button
                key={t.key}
                type="button"
                className={`nav-tab${active ? " nav-tab--active" : ""}`}
                aria-current={active ? "page" : undefined}
                onClick={() => navigate(t.key)}
              >
                <span className="nav-tab__icon">{t.icon}</span>
                <span className="nav-tab__label">{t.label}</span>
              </button>
            );
          })}
        </div>
      </nav>

      <Content style={{ padding: screens.md ? 24 : 12 }}>
        <Routes>
          <Route path="/" element={<Navigate to="/tableau-analysis" replace />} />
          <Route path="/tableau-analysis" element={<TableauAnalysis />} />
          <Route path="/data-source-details" element={<DataSourceDetails />} />
          <Route path="/dax-formula" element={<DaxFormula />} />
          {/* Backward-compatible redirect from the former "Calculations" route. */}
          <Route path="/calculations" element={<Navigate to="/dax-formula" replace />} />
          <Route path="/dashboards-worksheets" element={<DashboardsWorksheets />} />
          <Route path="/well-architected" element={<WellArchitected />} />
          <Route path="/migration-assessment" element={<MigrationAssessment />} />
          <Route path="*" element={<Navigate to="/tableau-analysis" replace />} />
        </Routes>
      </Content>

      <Footer style={{ textAlign: "center" }}>
        {APP_NAME} · {APP_VERSION} · Enterprise Tableau → Power BI Migration Assessment
      </Footer>
    </Layout>
  );
}
