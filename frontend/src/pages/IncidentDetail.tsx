import {
  Alert, Badge, Button, Card, Group, Modal, Select, SimpleGrid, Stack, Text, Textarea, TextInput, Timeline,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { IconCheck, IconLock, IconPlus, IconUserPlus } from "@tabler/icons-react";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useAction, useApi } from "../api";
import { useAuth } from "../auth";
import { TempChart } from "../TempChart";
import { code, DataTable, fmtDate, fmtDuration, fmtTime, label, PageHeader, Section, StatusBadge } from "../ui";
import { DecisionModal } from "./BatchTrace";

export default function IncidentDetailPage() {
  const { id } = useParams();
  const { data, error } = useApi<any>(`/incidents/${id}`, 4000);
  const { can, user } = useAuth();
  const navigate = useNavigate();
  const [decision, setDecision] = useState<{ batch_id: number; batch_status: string } | null>(null);
  const [assess, setAssess] = useState<any | null>(null);
  const [statusOpen, statusModal] = useDisclosure();
  const [nextStatus, setNextStatus] = useState<string>("resolved");

  if (error) return <Alert color="red">{(error as Error).message}</Alert>;
  if (!data) return null;
  const inc = data.incident;
  const active = ["open", "investigating", "resolved"].includes(inc.incident_status);
  const investigatorOrQm = can("investigator", "quality_manager");

  return (
    <Stack>
      <PageHeader
        title={`Incident ${inc.incident_code}`}
        subtitle={<Group gap="xs">
          <StatusBadge value={inc.incident_status} /><StatusBadge value={inc.severity} />
          <Text size="sm">{label(inc.incident_type)} · {label(inc.detection_source)} ·{" "}
            {inc.shipment_id
              ? <Text span c="cyan" style={{ cursor: "pointer" }} onClick={() => navigate(`/shipments/${inc.shipment_id}`)}>
                  shipment {code.shipment(inc.shipment_id)}</Text>
              : <>facility {inc.facility_name}</>}</Text></Group>}
        actions={<>
          {inc.incident_status === "investigating" && investigatorOrQm &&
            <Button leftSection={<IconCheck size={16} />} onClick={() => { setNextStatus("resolved"); statusModal.open(); }}>
              Mark resolved</Button>}
          {inc.incident_status === "resolved" && can("quality_manager") && <>
            <Button variant="default" onClick={() => { setNextStatus("investigating"); statusModal.open(); }}>Reopen</Button>
            <Button color="teal" leftSection={<IconLock size={16} />} onClick={() => { setNextStatus("closed"); statusModal.open(); }}>
              Close incident</Button>
          </>}
        </>} />

      <SimpleGrid cols={{ base: 2, md: 5 }}>
        <Fact t="Detected" v={fmtTime(inc.detected_at)} />
        <Fact t="Started" v={fmtTime(inc.start_time)} />
        <Fact t="Back in range" v={inc.end_time ? fmtTime(inc.end_time) : inc.start_time ? "Not yet" : "—"} warn={!inc.end_time && !!inc.start_time} />
        <Fact t="Exposure" v={fmtDuration(inc.exposure_seconds)} />
        <Fact t="Peak" v={inc.peak_temperature != null ? `${inc.peak_temperature} °C` : "—"} warn />
      </SimpleGrid>
      {inc.description && <Text size="sm" c="dimmed">{inc.description}</Text>}

      {data.context_readings.length > 0 && (
        <Section title="Relevant readings">
          <TempChart readings={data.context_readings} min={data.limits?.min_temp} max={data.limits?.max_temp} />
          <Text size="xs" c="dimmed" mt="xs">
            {data.readings.length} readings are linked to this incident. Limits shown are the tightest range of the products on board.
          </Text>
        </Section>
      )}

      <Section title="Potentially affected batches">
        <Text size="xs" c="dimmed" mb="xs">Only batches whose own product limits were breached are listed. Decisions are recorded
          by authorised staff; the system does not decide whether a medicine is usable.</Text>
        <DataTable rows={data.batches} empty="No batches linked." columns={[
          { key: "batch_number", title: "Batch", render: (r) =>
            <Text size="sm" fw={600} c="cyan" style={{ cursor: "pointer" }} onClick={() => navigate(`/batches/${r.batch_id}`)}>
              {r.batch_number}</Text> },
          { key: "product_name", title: "Product" },
          { key: "limits", title: "Limits", render: (r) => `${r.min_temp} to ${r.max_temp} °C` },
          { key: "current_quantity", title: "Units", align: "right" },
          { key: "assessment_status", title: "Assessment", render: (r) => <StatusBadge value={r.assessment_status} /> },
          { key: "assessment_note", title: "Note" },
          { key: "batch_status", title: "Batch status", render: (r) => <StatusBadge value={r.batch_status} /> },
          ...(investigatorOrQm && active ? [{ key: "act", title: "", render: (r: any) => (
            <Group gap={4} wrap="nowrap">
              <Button size="compact-xs" variant="light" onClick={() => setAssess(r)}>Assess</Button>
              <Button size="compact-xs" variant="light" color="orange" onClick={() => setDecision(r)}>Decision</Button>
            </Group>) }] : []),
        ]} />
      </Section>

      <SimpleGrid cols={{ base: 1, lg: 2 }}>
        <Investigations data={data} incidentId={Number(id)} active={active} />
        <Actions data={data} active={active} userId={user!.staff_id} />
      </SimpleGrid>

      <SimpleGrid cols={{ base: 1, lg: 2 }}>
        <Section title="Other shipments that may be affected">
          <DataTable rows={data.related_shipments} onRowClick={(r) => navigate(`/shipments/${r.shipment_id}`)}
            empty="No other shipment used the same vehicle or facility during this window." columns={[
              { key: "id", title: "Shipment", render: (r) => code.shipment(r.shipment_id) },
              { key: "reason", title: "Why" },
              { key: "dispatch_time", title: "Dispatched" },
              { key: "shipment_status", title: "Status", render: (r) => <StatusBadge value={r.shipment_status} /> },
            ]} />
        </Section>
        <Section title="History (audit log)">
          <Timeline bulletSize={12}>
            {data.history.map((h: any, i: number) => (
              <Timeline.Item key={i} title={h.action === "INSERT" ? "Incident created" : `${label(h.from_status)} → ${label(h.to_status)}`}>
                <Text size="xs" c="dimmed">{fmtTime(h.changed_at)} · {h.staff_name ?? "system"}</Text>
                {h.reason && <Text size="sm">{h.reason}</Text>}
              </Timeline.Item>
            ))}
          </Timeline>
        </Section>
      </SimpleGrid>

      {decision && <DecisionModal batchId={decision.batch_id} current={decision.batch_status} opened onClose={() => setDecision(null)} />}
      {assess && <AssessModal incidentId={Number(id)} row={assess} onClose={() => setAssess(null)} />}
      <StatusModal incidentId={Number(id)} status={nextStatus} opened={statusOpen} onClose={statusModal.close} />
    </Stack>
  );
}

function Fact({ t, v, warn }: { t: string; v: string; warn?: boolean }) {
  return (
    <Card withBorder padding="sm" radius="md">
      <Text size="xs" c="dimmed" tt="uppercase" fw={600}>{t}</Text>
      <Text fw={700} c={warn && v !== "—" ? "red" : undefined}>{v}</Text>
    </Card>
  );
}

function Investigations({ data, incidentId, active }: { data: any; incidentId: number; active: boolean }) {
  const { can, user } = useAuth();
  const staff = useApi<any[]>("/staff").data ?? [];
  const [assignee, setAssignee] = useState<string | null>(null);
  const assign = useAction("POST", () => `/incidents/${incidentId}/investigations`, "Investigator assigned");
  const update = useAction<{ id: number; body: any }>("PATCH", (v) => `/investigations/${v.id}`, "Investigation updated");
  const [findings, setFindings] = useState<Record<number, string>>({});

  return (
    <Section title="Investigation">
      <Stack>
        {data.investigations.length === 0 && <Text size="sm" c="dimmed">No investigator assigned yet.</Text>}
        {data.investigations.map((iv: any) => {
          const mine = can("quality_manager") || iv.assigned_to === user?.staff_id;
          return (
            <Card key={iv.investigation_id} withBorder padding="sm">
              <Group justify="space-between">
                <Text fw={600}>{iv.assignee}</Text>
                <StatusBadge value={iv.investigation_status} />
              </Group>
              <Text size="xs" c="dimmed">Started {fmtTime(iv.started_at)}{iv.completed_at && ` · completed ${fmtTime(iv.completed_at)}`}</Text>
              {iv.investigation_status === "completed" || !mine || !active ? (
                <Text size="sm" mt="xs">{iv.findings ?? "No findings recorded yet."}</Text>
              ) : (
                <Stack gap="xs" mt="xs">
                  <Textarea placeholder="Findings" minRows={2} value={findings[iv.investigation_id] ?? iv.findings ?? ""}
                    onChange={(e) => setFindings({ ...findings, [iv.investigation_id]: e.target.value })} />
                  <Group gap="xs">
                    <Button size="xs" variant="default" onClick={() => update.mutate({ id: iv.investigation_id,
                      body: { findings: findings[iv.investigation_id] ?? iv.findings, investigation_status: "in_progress" } })}>
                      Save findings</Button>
                    <Button size="xs" onClick={() => update.mutate({ id: iv.investigation_id,
                      body: { findings: findings[iv.investigation_id] ?? iv.findings, investigation_status: "completed" } })}>
                      Complete investigation</Button>
                  </Group>
                </Stack>
              )}
            </Card>
          );
        })}
        {can("quality_manager") && active && (
          <Group align="flex-end">
            <Select label="Assign investigator" style={{ flex: 1 }} value={assignee} onChange={setAssignee}
              data={staff.filter((s) => ["investigator", "quality_manager"].includes(s.role) && s.account_status === "active")
                .map((s) => ({ value: String(s.staff_id), label: `${s.staff_name} (${label(s.role)})` }))} />
            <Button leftSection={<IconUserPlus size={16} />} disabled={!assignee} loading={assign.isPending}
              onClick={() => assign.mutate({ assigned_to: Number(assignee) })}>Assign</Button>
          </Group>
        )}
      </Stack>
    </Section>
  );
}

function Actions({ data, active, userId }: { data: any; active: boolean; userId: number }) {
  const { can } = useAuth();
  const [opened, { open, close }] = useDisclosure();
  const update = useAction<{ id: number; body: any }>("PATCH", (v) => `/actions/${v.id}`, "Corrective action updated");
  const investigation = data.investigations[data.investigations.length - 1];
  return (
    <Section title="Corrective actions" actions={can("investigator", "quality_manager") && active && investigation &&
      <Button size="xs" variant="light" leftSection={<IconPlus size={14} />} onClick={open}>Add</Button>}>
      <DataTable rows={data.actions} empty="No corrective actions yet." columns={[
        { key: "action_description", title: "Action" },
        { key: "assignee", title: "Responsible" },
        { key: "due_date", title: "Due", render: (r) => {
          const overdue = r.due_date && ["pending", "in_progress"].includes(r.action_status) && new Date(r.due_date) < new Date();
          return <Group gap={4}>{fmtDate(r.due_date)}{overdue && <Badge size="xs" color="red">overdue</Badge>}</Group>; } },
        { key: "action_status", title: "Status", render: (r) =>
          active && (can("investigator", "quality_manager") || r.assigned_to === userId) && !["completed", "cancelled"].includes(r.action_status)
            ? <Select size="xs" w={140} value={r.action_status} allowDeselect={false}
                data={[{ value: "pending", label: "Pending" }, { value: "in_progress", label: "In progress" },
                       { value: "completed", label: "Completed" }, { value: "cancelled", label: "Cancelled" }]}
                onChange={(v) => v && update.mutate({ id: r.action_id, body: { action_status: v } })} />
            : <StatusBadge value={r.action_status} /> },
      ]} />
      {investigation && <NewAction investigationId={investigation.investigation_id} opened={opened} onClose={close} />}
    </Section>
  );
}

function NewAction({ investigationId, opened, onClose }: { investigationId: number; opened: boolean; onClose: () => void }) {
  const staff = useApi<any[]>(opened ? "/staff" : null).data ?? [];
  const [desc, setDesc] = useState("");
  const [who, setWho] = useState<string | null>(null);
  const [due, setDue] = useState("");
  const add = useAction("POST", () => `/investigations/${investigationId}/actions`, "Corrective action added", () => {
    setDesc(""); setWho(null); setDue(""); onClose();
  });
  return (
    <Modal opened={opened} onClose={onClose} title="Add corrective action">
      <Stack>
        <Textarea label="Action required" minRows={2} value={desc} onChange={(e) => setDesc(e.target.value)} />
        <Select label="Responsible" value={who} onChange={setWho}
          data={staff.filter((s) => s.account_status === "active").map((s) => ({ value: String(s.staff_id), label: s.staff_name }))} />
        <TextInput type="date" label="Due date" value={due} onChange={(e) => setDue(e.target.value)} />
        <Button disabled={desc.trim().length < 5 || !who} loading={add.isPending}
          onClick={() => add.mutate({ action_description: desc, assigned_to: Number(who), due_date: due || null })}>Add</Button>
      </Stack>
    </Modal>
  );
}

function AssessModal({ incidentId, row, onClose }: { incidentId: number; row: any; onClose: () => void }) {
  const [status, setStatus] = useState<string | null>(row.assessment_status);
  const [note, setNote] = useState(row.assessment_note ?? "");
  const save = useAction("PATCH", () => `/incidents/${incidentId}/batches/${row.batch_id}`, "Assessment saved", onClose);
  return (
    <Modal opened onClose={onClose} title={`Assess batch ${row.batch_number}`}>
      <Stack>
        <Select label="Assessment" value={status} onChange={setStatus}
          data={[{ value: "pending_review", label: "Pending review" }, { value: "under_assessment", label: "Under assessment" },
                 { value: "assessed", label: "Assessed" }]} />
        <Textarea label="Note" description="Required when marking as assessed" minRows={3} value={note}
          onChange={(e) => setNote(e.target.value)} />
        <Button loading={save.isPending} disabled={status === "assessed" && note.trim().length === 0}
          onClick={() => save.mutate({ assessment_status: status, assessment_note: note || null })}>Save</Button>
      </Stack>
    </Modal>
  );
}

function StatusModal({ incidentId, status, opened, onClose }: { incidentId: number; status: string; opened: boolean; onClose: () => void }) {
  const [reason, setReason] = useState("");
  const save = useAction("POST", () => `/incidents/${incidentId}/status`, `Incident ${label(status).toLowerCase()}`, () => {
    setReason(""); onClose();
  });
  return (
    <Modal opened={opened} onClose={onClose} title={`${label(status)} incident`}>
      <Stack>
        {status === "closed" && <Alert color="blue" variant="light">
          The database only allows closing when every investigation and corrective action is finished and every affected
          batch is assessed.</Alert>}
        <Textarea label="Reason" minRows={2} value={reason} onChange={(e) => setReason(e.target.value)} />
        <Button disabled={reason.trim().length < 3} loading={save.isPending} onClick={() => save.mutate({ status, reason })}>
          Confirm</Button>
      </Stack>
    </Modal>
  );
}
