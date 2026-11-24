import { lazy, Suspense } from "react";
import { ActionIcon, AppShell, Badge, Burger, Center, Group, Loader, NavLink, Text, Tooltip, useComputedColorScheme, useMantineColorScheme } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import {
  IconActivityHeartbeat, IconAlertTriangle, IconBuildingWarehouse, IconChartBar, IconLayoutDashboard,
  IconLogout, IconMoon, IconPackage, IconPill, IconSun, IconTruckDelivery,
} from "@tabler/icons-react";
import { Link, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "./auth";
import { Brand } from "./Identity";
import { label } from "./ui";
import LoginPage from "./pages/Login";

const AdminPage = lazy(() => import("./pages/Admin"));
const BatchesPage = lazy(() => import("./pages/Batches"));
const BatchTracePage = lazy(() => import("./pages/BatchTrace"));
const DashboardPage = lazy(() => import("./pages/Dashboard"));
const IncidentDetailPage = lazy(() => import("./pages/IncidentDetail"));
const IncidentsPage = lazy(() => import("./pages/Incidents"));
const MonitoringPage = lazy(() => import("./pages/Monitoring"));
const ProductsPage = lazy(() => import("./pages/Products"));
const ReportsPage = lazy(() => import("./pages/Reports"));
const ShipmentDetailPage = lazy(() => import("./pages/ShipmentDetail"));
const ShipmentsPage = lazy(() => import("./pages/Shipments"));

const NAV = [
  { to: "/", label: "Dashboard", icon: IconLayoutDashboard },
  { to: "/shipments", label: "Shipments", icon: IconTruckDelivery },
  { to: "/batches", label: "Batches", icon: IconPackage },
  { to: "/products", label: "Products", icon: IconPill },
  { to: "/monitoring", label: "Monitoring", icon: IconActivityHeartbeat },
  { to: "/incidents", label: "Incidents", icon: IconAlertTriangle },
  { to: "/reports", label: "Reports", icon: IconChartBar },
  { to: "/admin", label: "Facilities & admin", icon: IconBuildingWarehouse },
];

export default function App() {
  const { user, loading, logout } = useAuth();
  const [opened, { toggle, close }] = useDisclosure();
  const { toggleColorScheme } = useMantineColorScheme();
  const colorScheme = useComputedColorScheme("light");
  const navigate = useNavigate();
  const location = useLocation();

  if (loading) return <Center h="100vh"><Loader /></Center>;
  if (!user) {
    return (
      <Routes>
        <Route path="*" element={<LoginPage />} />
      </Routes>
    );
  }

  const active = (to: string) => (to === "/" ? location.pathname === "/" : location.pathname.startsWith(to));

  return (
    <AppShell header={{ height: 64 }} navbar={{ width: 216, breakpoint: "sm", collapsed: { mobile: !opened } }} padding="lg" className="workspace">
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group gap="sm">
            <Burger aria-label="Toggle navigation" aria-expanded={opened} opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
            <Brand />
            <Text c="dimmed" size="sm" visibleFrom="md">Cold-chain traceability</Text>
          </Group>
          <Group gap="sm">
            <Text size="sm" visibleFrom="sm">{user.staff_name}</Text>
            <Badge variant="light">{label(user.role)}</Badge>
            <Tooltip label="Toggle theme">
              <ActionIcon variant="subtle" onClick={toggleColorScheme} aria-label="Toggle theme">
                {colorScheme === "dark" ? <IconSun size={18} /> : <IconMoon size={18} />}
              </ActionIcon>
            </Tooltip>
            <Tooltip label="Sign out">
              <ActionIcon variant="subtle" color="red" onClick={() => { logout(); navigate("/"); }} aria-label="Sign out">
                <IconLogout size={18} />
              </ActionIcon>
            </Tooltip>
          </Group>
        </Group>
      </AppShell.Header>
      <AppShell.Navbar p="sm" component="nav" aria-label="Main navigation">
        {NAV.map((n) => (
          <NavLink key={n.to} component={Link} to={n.to} aria-current={active(n.to) ? "page" : undefined} label={n.label} leftSection={<n.icon size={18} />} active={active(n.to)}
            onClick={close} />
        ))}
      </AppShell.Navbar>
      <AppShell.Main>
        <div className="page-view" key={location.pathname}>
          <Suspense fallback={<Center mih={240}><Loader aria-label="Loading page" /></Center>}>
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/shipments" element={<ShipmentsPage />} />
              <Route path="/shipments/:id" element={<ShipmentDetailPage />} />
              <Route path="/batches" element={<BatchesPage />} />
              <Route path="/batches/:id" element={<BatchTracePage />} />
              <Route path="/products" element={<ProductsPage />} />
              <Route path="/monitoring" element={<MonitoringPage />} />
              <Route path="/incidents" element={<IncidentsPage />} />
              <Route path="/incidents/:id" element={<IncidentDetailPage />} />
              <Route path="/reports" element={<ReportsPage />} />
              <Route path="/admin" element={<AdminPage />} />
              <Route path="*" element={<Navigate to="/" />} />
            </Routes>
          </Suspense>
        </div>
      </AppShell.Main>
    </AppShell>
  );
}
