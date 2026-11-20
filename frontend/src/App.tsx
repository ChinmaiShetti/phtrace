import { ActionIcon, AppShell, Badge, Burger, Center, Group, Loader, NavLink, Text, Tooltip, useMantineColorScheme } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import {
  IconActivityHeartbeat, IconAlertTriangle, IconBuildingWarehouse, IconChartBar, IconLayoutDashboard,
  IconLogout, IconMoon, IconPackage, IconPill, IconSun, IconTruckDelivery,
} from "@tabler/icons-react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "./auth";
import { label } from "./ui";
import AdminPage from "./pages/Admin";
import BatchesPage from "./pages/Batches";
import BatchTracePage from "./pages/BatchTrace";
import DashboardPage from "./pages/Dashboard";
import IncidentDetailPage from "./pages/IncidentDetail";
import IncidentsPage from "./pages/Incidents";
import LoginPage from "./pages/Login";
import MonitoringPage from "./pages/Monitoring";
import ProductsPage from "./pages/Products";
import ReportsPage from "./pages/Reports";
import ShipmentDetailPage from "./pages/ShipmentDetail";
import ShipmentsPage from "./pages/Shipments";

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
  const { colorScheme, toggleColorScheme } = useMantineColorScheme();
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
    <AppShell header={{ height: 56 }} navbar={{ width: 230, breakpoint: "sm", collapsed: { mobile: !opened } }} padding="lg">
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group gap="sm">
            <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
            <Text fw={800} size="lg">Pharma<Text span c="cyan" inherit>Trace</Text></Text>
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
      <AppShell.Navbar p="sm">
        {NAV.map((n) => (
          <NavLink key={n.to} label={n.label} leftSection={<n.icon size={18} />} active={active(n.to)}
            onClick={() => { navigate(n.to); close(); }} style={{ borderRadius: 8 }} />
        ))}
      </AppShell.Navbar>
      <AppShell.Main>
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
      </AppShell.Main>
    </AppShell>
  );
}
