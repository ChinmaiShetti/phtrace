import { Alert, Badge, Button, Group, Modal, NumberInput, Select, SimpleGrid, Stack, Text, TextInput, Timeline } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { IconCircleCheck, IconPlus, IconTruck, IconX } from "@tabler/icons-react";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useAction, useApi } from "../api";
import { useAuth } from "../auth";
import { code, DataTable, fmtDate, fmtTime, label, PageHeader, Section, StatusBadge } from "../ui";

export default function ShipmentDetailPage() {
  const { id } = useParams();
  const { data, error } = useApi<any>(`/shipments/${id}`);
  const { can } = useAuth();
  const navigate = useNavigate();
  const dispatch = useAction("POST", () => `/shipments/${id}/dispatch`, "Shipment dispatched");
  const receive = useAction("POST", () => `/shipments/${id}/receive`, "Shipment received at destination");
  const cancel = useAction("POST", () => `/shipments/${id}/cancel`, "Shipment cancelled");
  const removeLine = useAction<{ batch_id: number }>("DELETE", (v) => `/shipments/${id}/batches/${v.batch_id}`, "Batch removed");
  const [addOpen, addLine] = useDisclosure();
  const [cpOpen, checkpoint] = useDisclosure();

  if (error) return <Alert color="red">{(error as Error).message}</Alert>;
  if (!data) return null;
  const s = data.shipment;
  const operator = can("operator", "admin");

  return (
    <Stack>
      <PageHeader
        title={`Shipment ${code.shipment(s.shipment_id)}`}
        subtitle={<Group gap="xs"><StatusBadge value={s.shipment_status} />
          <Text size="sm">{s.origin_name} → {s.destination_name} · vehicle {s.registration_number}</Text></Group>}
        actions={operator && <>
          {s.shipment_status === "planned" && <>
            <Button leftSection={<IconTruck size={16} />} loading={dispatch.isPending} onClick={() => dispatch.mutate({})}>
              Dispatch</Button>
            <Button variant="default" color="red" leftSection={<IconX size={16} />} onClick={() => cancel.mutate({})}>Cancel</Button>
          </>}
          {s.shipment_status === "in_transit" && <>
            <Button variant="default" leftSection={<IconPlus size={16} />} onClick={checkpoint.open}>Checkpoint</Button>
            <Button color="teal" leftSection={<IconCircleCheck size={16} />} loading={receive.isPending}
              onClick={() => receive.mutate({})}>Confirm arrival</Button>
          </>}
        </>} />

      <SimpleGrid cols={{ base: 2, md: 4 }}>
        <Fact label="Dispatched" value={fmtTime(s.dispatch_time)} />
        <Fact label="Expected arrival" value={fmtTime(s.expected_arrival)} warn={s.overdue} />
        <Fact label="Arrived" value={fmtTime(s.actual_arrival)} />
        <Fact label="Storage range on board"
          value={data.limits ? `${data.limits.min_temp} to ${data.limits.max_temp} °C` : "—"} />
      </SimpleGrid>

      <Section title="Batches on board" actions={s.shipment_status === "planned" && can("operator", "quality_manager", "admin") &&
        <Button size="xs" variant="light" leftSection={<IconPlus size={14} />} onClick={addLine.open}>Add batch</Button>}>
        <DataTable rows={data.lines} onRowClick={(r) => navigate(`/batches/${r.batch_id}`)} columns={[
          { key: "batch_number", title: "Batch" },
          { key: "product_name", title: "Product" },
          { key: "range", title: "Limits", render: (r) => `${r.min_temp} to ${r.max_temp} °C` },
          { key: "quantity_shipped", title: "Quantity", align: "right" },
          { key: "expiry_date", title: "Expiry", render: (r) => fmtDate(r.expiry_date) },
          { key: "batch_status", title: "Batch status", render: (r) => <StatusBadge value={r.batch_status} /> },
          ...(s.shipment_status === "planned" ? [{ key: "x", title: "", render: (r: any) =>
            <Button size="compact-xs" variant="subtle" color="red"
              onClick={(e) => { e.stopPropagation(); removeLine.mutate({ batch_id: r.batch_id }); }}>Remove</Button> }] : []),
        ]} />
      </Section>

      <SimpleGrid cols={{ base: 1, lg: 2 }}>
        <Section title="Timeline">
          <Timeline bulletSize={14} lineWidth={2}>
            {data.timeline.map((t: any, i: number) => (
              <Timeline.Item key={i} title={label(t.event_kind.split(":")[1])}
                color={t.event_kind.startsWith("incident") ? "red" : t.event_kind.startsWith("movement") ? "cyan" : "gray"}>
                <Text size="xs" c="dimmed">{fmtTime(t.event_time)}</Text>
                <Text size="sm">{t.detail}</Text>
              </Timeline.Item>
            ))}
          </Timeline>
          {data.timeline.length === 0 && <Text c="dimmed" size="sm">Not dispatched yet.</Text>}
        </Section>
        <Stack>
          <Section title="Monitoring sensors">
            <DataTable rows={data.sensors} empty="No sensor attached: dispatch is blocked until one is assigned."
              columns={[
                { key: "serial_number", title: "Sensor" },
                { key: "assigned_at", title: "Attached" },
                { key: "unassigned_at", title: "Removed" },
              ]} />
          </Section>
          <Section title="Incidents">
            <DataTable rows={data.incidents} onRowClick={(r) => navigate(`/incidents/${r.incident_id}`)}
              empty="No incidents on this shipment." columns={[
                { key: "incident_code", title: "Incident" },
                { key: "severity", title: "Severity", render: (r) => <StatusBadge value={r.severity} /> },
                { key: "incident_status", title: "Status", render: (r) => <StatusBadge value={r.incident_status} /> },
                { key: "detected_at", title: "Detected" },
              ]} />
          </Section>
        </Stack>
      </SimpleGrid>
      <AddLine shipmentId={Number(id)} opened={addOpen} onClose={addLine.close} />
      <AddCheckpoint shipmentId={Number(id)} opened={cpOpen} onClose={checkpoint.close} />
    </Stack>
  );
}

function Fact({ label: l, value, warn }: { label: string; value: string; warn?: boolean }) {
  return (
    <div>
      <Text size="xs" c="dimmed" tt="uppercase" fw={600}>{l}</Text>
      <Group gap={6}><Text fw={600} c={warn ? "red" : undefined}>{value}</Text>{warn && <Badge color="red" size="xs">overdue</Badge>}</Group>
    </div>
  );
}

function AddLine({ shipmentId, opened, onClose }: { shipmentId: number; opened: boolean; onClose: () => void }) {
  const batches = useApi<any[]>(opened ? "/batches" : null).data ?? [];
  const [batch, setBatch] = useState<string | null>(null);
  const [qty, setQty] = useState<number | string>(100);
  const add = useAction("POST", () => `/shipments/${shipmentId}/batches`, "Batch added", onClose);
  return (
    <Modal opened={opened} onClose={onClose} title="Add batch to shipment">
      <Stack>
        <Select label="Batch" searchable value={batch} onChange={setBatch}
          data={batches.filter((b) => ["available", "released"].includes(b.batch_status))
            .map((b) => ({ value: String(b.batch_id), label: `${b.batch_number} · ${b.product_name} · ${b.on_hand} on hand` }))} />
        <NumberInput label="Quantity" min={1} value={qty} onChange={setQty} />
        <Button disabled={!batch} loading={add.isPending}
          onClick={() => add.mutate({ batch_id: Number(batch), quantity_shipped: Number(qty) })}>Add</Button>
      </Stack>
    </Modal>
  );
}

function AddCheckpoint({ shipmentId, opened, onClose }: { shipmentId: number; opened: boolean; onClose: () => void }) {
  const [type, setType] = useState<string | null>("transit_scan");
  const [where, setWhere] = useState("");
  const add = useAction("POST", () => `/shipments/${shipmentId}/checkpoints`, "Checkpoint recorded", onClose);
  return (
    <Modal opened={opened} onClose={onClose} title="Record checkpoint">
      <Stack>
        <Select label="Event" value={type} onChange={setType}
          data={[{ value: "transit_scan", label: "Transit scan" }, { value: "inspection", label: "Inspection" },
                 { value: "delay", label: "Delay" }]} />
        <TextInput label="Location" placeholder="e.g. NH48 toll plaza" value={where} onChange={(e) => setWhere(e.target.value)} />
        <Button disabled={where.trim().length < 2} loading={add.isPending}
          onClick={() => add.mutate({ event_type: type, location_description: where })}>Save</Button>
      </Stack>
    </Modal>
  );
}
