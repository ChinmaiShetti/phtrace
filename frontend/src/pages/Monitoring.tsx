import { Badge, Group, Select, Stack, Switch } from "@mantine/core";
import { useState } from "react";
import { useApi } from "../api";
import { TempChart } from "../TempChart";
import { code, DataTable, PageHeader, Section, StatusBadge } from "../ui";

const WINDOWS: Record<string, number> = { "1h": 1, "6h": 6, "24h": 24, "7d": 168 };

export default function MonitoringPage() {
  const sensors = useApi<any[]>("/sensors").data ?? [];
  const shipments = useApi<any[]>("/shipments").data ?? [];
  const [sensor, setSensor] = useState<string | null>(null);
  const [shipment, setShipment] = useState<string | null>(null);
  const [range, setRange] = useState<string>("6h");
  const [quality, setQuality] = useState<string | null>(null);
  const [outOnly, setOutOnly] = useState(false);

  const since = new Date(Date.now() - WINDOWS[range] * 3600_000);
  since.setSeconds(0, 0);
  const params = new URLSearchParams({ from: since.toISOString(), limit: "2000" });
  if (sensor) params.set("sensor_id", sensor);
  if (shipment) params.set("shipment_id", shipment);
  if (quality) params.set("quality", quality);
  if (outOnly) params.set("out_of_limits", "true");
  const { data } = useApi<any[]>(`/readings?${params}`, 10_000);

  const chartable = sensor || shipment;
  const first = data?.find((r) => r.max_temp != null);

  return (
    <Stack>
      <PageHeader title="Monitoring" subtitle="Original readings are never edited; invalid and suspicious values are only flagged." />
      <Group align="flex-end">
        <Select label="Sensor" clearable searchable w={200} value={sensor} onChange={(v) => { setSensor(v); setShipment(null); }}
          data={sensors.map((s) => ({ value: String(s.sensor_id), label: s.serial_number }))} />
        <Select label="Shipment" clearable w={220} value={shipment} onChange={(v) => { setShipment(v); setSensor(null); }}
          data={shipments.filter((s) => s.dispatch_time).map((s) => ({ value: String(s.shipment_id),
            label: `${code.shipment(s.shipment_id)} → ${s.destination_name}` }))} />
        <Select label="Window" w={100} value={range} onChange={(v) => setRange(v ?? "6h")} data={Object.keys(WINDOWS)} />
        <Select label="Quality" clearable w={140} value={quality} onChange={setQuality}
          data={["valid", "suspicious", "invalid"]} />
        <Switch label="Outside limits only" checked={outOnly} onChange={(e) => setOutOnly(e.currentTarget.checked)} mb={8} />
      </Group>
      {chartable && (
        <Section title="Temperature">
          <TempChart readings={data ?? []} min={first?.min_temp} max={first?.max_temp} />
        </Section>
      )}
      <Section title={`${data?.length ?? 0} readings`}>
        <DataTable rows={data?.slice(0, 300)} rowKey={(r) => r.reading_id} columns={[
          { key: "recorded_at", title: "Recorded" },
          { key: "serial_number", title: "Sensor" },
          { key: "target", title: "Monitoring", render: (r) =>
            r.shipment_id ? code.shipment(r.shipment_id) : r.facility_id ? `Facility ${r.facility_id}` : "Unassigned" },
          { key: "temperature", title: "°C", align: "right" },
          { key: "humidity", title: "% RH", align: "right" },
          { key: "limits", title: "Limits", render: (r) => (r.max_temp == null ? "—" : `${r.min_temp} to ${r.max_temp}`) },
          { key: "out_of_limits", title: "Breach", render: (r) => (r.out_of_limits ? <Badge color="red" size="sm">Out of range</Badge> : "") },
          { key: "quality_status", title: "Quality", render: (r) => <StatusBadge value={r.quality_status} /> },
        ]} />
      </Section>
    </Stack>
  );
}
