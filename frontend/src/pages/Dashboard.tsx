import { Button, Card, Group, NumberInput, Select, SimpleGrid, Stack, Text } from "@mantine/core";
import { ThermalField } from "../Identity";
import { IconArrowUpRight, IconFlame, IconRefresh, IconTruckDelivery } from "@tabler/icons-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAction, useApi } from "../api";
import { useAuth } from "../auth";
import { code, DataTable, ErrorNote, fmtTime, label, PageHeader, Section, StatusBadge } from "../ui";

const TILES: [string, string, string][] = [
  ["open_incidents", "Open incidents", "red"],
  ["batches_under_investigation", "Batches under investigation", "orange"],
  ["batches_on_hold", "Batches on hold or quarantined", "orange"],
  ["overdue_actions", "Overdue corrective actions", "grape"],
  ["excursions_last_7_days", "Excursions in last 7 days", "red"],
  ["overdue_arrivals", "Shipments overdue for arrival", "yellow"],
];

export default function DashboardPage() {
  const { data, error } = useApi<any>("/dashboard", 5000);
  const navigate = useNavigate();
  const { can } = useAuth();
  const counts = data?.counts ?? {};

  return (
    <Stack>
      <PageHeader title="Dashboard" subtitle="Shipment activity and cold-chain exceptions." actions={
        <span className="refresh-note"><IconRefresh size={14} /> Refreshes every 5 s</span>
      } />
      <ErrorNote error={error} />
      <div className="overview">
        <button className="fleet-card" onClick={() => navigate("/shipments")}>
          <span className="fleet-label"><IconTruckDelivery size={19} /> Active shipments</span>
          <strong>{counts.active_shipments ?? "–"}</strong>
          <ThermalField />
          <span className="fleet-link">View shipments <IconArrowUpRight size={16} /></span>
        </button>
        <div className="metrics">{TILES.map(([key, title, color]) => (
          <div className="metric" key={key}>
            <Text size="sm" c="dimmed">{title}</Text>
            <Text className="metric-value" c={counts[key] > 0 ? `light-dark(var(--mantine-color-${color}-9), var(--mantine-color-${color}-3))` : undefined}>{counts[key] ?? "–"}</Text>
          </div>
        ))}</div>
      </div>
      <SimpleGrid cols={{ base: 1, xl: 2 }}>
        <Section title="Shipments in transit">
          <DataTable rows={data?.active_shipments} onRowClick={(r) => navigate(`/shipments/${r.shipment_id}`)}
            empty="No shipments on the road."
            columns={[
              { key: "id", title: "Shipment", render: (r) => code.shipment(r.shipment_id) },
              { key: "route", title: "Route", render: (r) => `${r.origin_name} → ${r.destination_name}` },
              { key: "registration_number", title: "Vehicle" },
              { key: "expected_arrival", title: "Expected", render: (r) => (
                <Text size="sm" c={r.overdue ? "red" : undefined} fw={r.overdue ? 700 : undefined}>
                  {fmtTime(r.expected_arrival)}{r.overdue ? " (overdue)" : ""}
                </Text>) },
            ]} />
        </Section>
        <Section title="Recent incidents">
          <DataTable rows={data?.recent_incidents} onRowClick={(r) => navigate(`/incidents/${r.incident_id}`)}
            columns={[
              { key: "incident_code", title: "Incident" },
              { key: "incident_type", title: "Type", render: (r) => label(r.incident_type) },
              { key: "severity", title: "Severity", render: (r) => <StatusBadge value={r.severity} /> },
              { key: "incident_status", title: "Status", render: (r) => <StatusBadge value={r.incident_status} /> },
              { key: "detected_at", title: "Detected" },
            ]} />
        </Section>
      </SimpleGrid>
      {can("admin") && <Simulator shipments={data?.active_shipments ?? []} />}
    </Stack>
  );
}

function Simulator({ shipments }: { shipments: any[] }) {
  const [shipment, setShipment] = useState<string | null>(null);
  const [peak, setPeak] = useState<number | string>(11.5);
  const simulate = useAction("POST", () => "/admin/simulate-excursion",
    "Refrigeration failure started: a reading arrives every 2.5 s. Watch the incidents list.");
  const backfill = useAction("POST", () => "/admin/backfill", "Sensor feed brought up to date");
  return (
    <Card withBorder radius="md" padding="md" className="simulator">
      <Group align="flex-end" wrap="wrap">
        <div style={{ flex: 1, minWidth: 220 }}>
          <Text fw={700}>Refrigeration failure simulator</Text>
          <Text size="sm" c="dimmed">Send rising temperature readings to demonstrate how an incident opens.</Text>
        </div>
        <Select label="Shipment" placeholder="In-transit shipment" w={260} value={shipment} onChange={setShipment}
          data={shipments.map((s) => ({ value: String(s.shipment_id),
            label: `${code.shipment(s.shipment_id)} → ${s.destination_name}` }))} />
        <NumberInput label="Peak °C" w={100} value={peak} onChange={setPeak} step={0.5} />
        <Button color="red" leftSection={<IconFlame size={16} />} disabled={!shipment} loading={simulate.isPending}
          onClick={() => simulate.mutate({ shipment_id: Number(shipment), peak_temperature: Number(peak) })}>
          Simulate failure
        </Button>
        <Button variant="default" leftSection={<IconRefresh size={16} />} loading={backfill.isPending}
          onClick={() => backfill.mutate({})}>
          Catch up sensor feed
        </Button>
      </Group>
    </Card>
  );
}
