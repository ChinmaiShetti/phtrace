import { Alert, Button, Group, Modal, Select, SimpleGrid, Stack, Text, Textarea, Timeline } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { IconArrowsExchange } from "@tabler/icons-react";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useAction, useApi } from "../api";
import { useAuth } from "../auth";
import { code, DataTable, fmtDate, fmtDuration, fmtTime, label, PageHeader, Section, StatusBadge } from "../ui";

export default function BatchTracePage() {
  const { id } = useParams();
  const { data, error } = useApi<any>(`/batches/${id}/trace`);
  const { can } = useAuth();
  const navigate = useNavigate();
  const [opened, { open, close }] = useDisclosure();

  if (error) return <Alert color="red">{(error as Error).message}</Alert>;
  if (!data) return null;
  const b = data.batch;

  return (
    <Stack>
      <PageHeader title={`Batch ${b.batch_number}`}
        subtitle={<Group gap="xs"><StatusBadge value={b.batch_status} />
          <Text size="sm">{b.product_name} · {data.product.min_temp} to {data.product.max_temp} °C · expires {fmtDate(b.expiry_date)}
            {b.is_expired && <Text span c="red" fw={700}> (expired)</Text>}</Text></Group>}
        actions={can("investigator", "quality_manager") &&
          <Button leftSection={<IconArrowsExchange size={16} />} onClick={open}>Record decision</Button>} />

      <SimpleGrid cols={{ base: 2, md: 4 }}>
        <Stat title="Initial quantity" value={b.initial_quantity} />
        <Stat title="On hand (all facilities)" value={b.on_hand} />
        <Stat title="In transit" value={b.in_transit} />
        <Stat title="Open incidents" value={b.open_incidents} warn={b.open_incidents > 0} />
      </SimpleGrid>

      <SimpleGrid cols={{ base: 1, lg: 2 }}>
        <Section title="Where it is now">
          <DataTable rows={data.stock} empty="No stock recorded at any facility." columns={[
            { key: "facility_name", title: "Facility" }, { key: "on_hand", title: "On hand", align: "right" }]} />
        </Section>
        <Section title="Decisions (status history)">
          <DataTable rows={data.status_history} empty="No status changes recorded." columns={[
            { key: "changed_at", title: "When" },
            { key: "change", title: "Change", render: (r) => <Group gap={4}><StatusBadge value={r.from_status} />→<StatusBadge value={r.to_status} /></Group> },
            { key: "staff_name", title: "By" },
            { key: "reason", title: "Reason" },
          ]} />
        </Section>
      </SimpleGrid>

      <Section title="Chain of custody (movement history)">
        <Timeline bulletSize={14}>
          {data.movements.map((m: any) => (
            <Timeline.Item key={m.movement_id} title={`${label(m.movement_type)} · ${m.quantity_moved} units`}
              color={m.movement_type === "received" ? "teal" : m.movement_type === "dispatched" ? "blue" : "red"}>
              <Text size="sm">{m.facility_name}{m.shipment_id ? ` · ${code.shipment(m.shipment_id)}` : " · intake"}</Text>
              <Text size="xs" c="dimmed">{fmtTime(m.movement_time)}</Text>
            </Timeline.Item>
          ))}
        </Timeline>
      </Section>

      <SimpleGrid cols={{ base: 1, lg: 2 }}>
        <Section title="Shipments">
          <DataTable rows={data.shipments} onRowClick={(r) => navigate(`/shipments/${r.shipment_id}`)} columns={[
            { key: "id", title: "Shipment", render: (r) => code.shipment(r.shipment_id) },
            { key: "route", title: "Route", render: (r) => `${r.origin_name} → ${r.destination_name}` },
            { key: "quantity_shipped", title: "Qty", align: "right" },
            { key: "shipment_status", title: "Status", render: (r) => <StatusBadge value={r.shipment_status} /> },
          ]} />
        </Section>
        <Section title="Incidents and assessments">
          <DataTable rows={data.incidents} onRowClick={(r) => navigate(`/incidents/${r.incident_id}`)}
            empty="This batch has never been involved in an incident." columns={[
              { key: "incident_code", title: "Incident" },
              { key: "peak_temperature", title: "Peak °C", align: "right" },
              { key: "exposure_seconds", title: "Exposure", align: "right", render: (r) => fmtDuration(r.exposure_seconds) },
              { key: "assessment_status", title: "Assessment", render: (r) => <StatusBadge value={r.assessment_status} /> },
              { key: "incident_status", title: "Incident", render: (r) => <StatusBadge value={r.incident_status} /> },
            ]} />
        </Section>
      </SimpleGrid>
      <DecisionModal batchId={Number(id)} current={b.batch_status} opened={opened} onClose={close} />
    </Stack>
  );
}

function Stat({ title, value, warn }: { title: string; value: number; warn?: boolean }) {
  return (
    <div>
      <Text size="xs" c="dimmed" tt="uppercase" fw={600}>{title}</Text>
      <Text fz={26} fw={800} c={warn ? "red" : undefined}>{value}</Text>
    </div>
  );
}

export function DecisionModal({ batchId, current, opened, onClose }:
  { batchId: number; current: string; opened: boolean; onClose: () => void }) {
  const { user } = useAuth();
  const transitions = useApi<any[]>(opened ? "/batch-transitions" : null).data ?? [];
  const allowed = transitions.filter((t) => t.from_status === current && t.role === user?.role).map((t) => t.to_status);
  const [status, setStatus] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const save = useAction("POST", () => `/batches/${batchId}/status`, "Decision recorded", () => {
    setStatus(null); setReason(""); onClose();
  });
  return (
    <Modal opened={opened} onClose={onClose} title="Record batch decision">
      <Stack>
        <Text size="sm">Current status: <StatusBadge value={current} /></Text>
        {allowed.length === 0
          ? <Alert color="gray">Your role cannot change a batch that is {label(current).toLowerCase()}.</Alert>
          : <Select label="New status" value={status} onChange={setStatus}
              data={allowed.map((s) => ({ value: s, label: label(s) }))} />}
        <Textarea label="Reason" description="Stored in the audit log with your name and the time"
          minRows={2} value={reason} onChange={(e) => setReason(e.target.value)} />
        <Text size="xs" c="dimmed">PharmaTrace records the decision; it does not judge whether the medicine is safe.</Text>
        <Button disabled={!status || reason.trim().length < 3} loading={save.isPending}
          onClick={() => save.mutate({ status, reason })}>Save decision</Button>
      </Stack>
    </Modal>
  );
}
