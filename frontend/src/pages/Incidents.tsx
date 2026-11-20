import { Button, Group, Modal, SegmentedControl, Select, Stack, Text, Textarea, TextInput } from "@mantine/core";
import { useForm } from "@mantine/form";
import { useDisclosure } from "@mantine/hooks";
import { IconPlus } from "@tabler/icons-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAction, useApi } from "../api";
import { useAuth } from "../auth";
import { code, DataTable, fmtDuration, label, opts, PageHeader, Section, StatusBadge } from "../ui";

export default function IncidentsPage() {
  const [status, setStatus] = useState("all");
  const { data } = useApi<any[]>(status === "all" ? "/incidents" : `/incidents?status=${status}`, 5000);
  const navigate = useNavigate();
  const { can } = useAuth();
  const [opened, { open, close }] = useDisclosure();

  return (
    <Stack>
      <PageHeader title="Incidents" subtitle="Excursions are raised automatically by the database; others can be reported here."
        actions={can("operator", "investigator", "quality_manager") &&
          <Button leftSection={<IconPlus size={16} />} onClick={open}>Report incident</Button>} />
      <SegmentedControl w="fit-content" value={status} onChange={setStatus}
        data={[{ value: "all", label: "All" }, ...opts(["open", "investigating", "resolved", "closed"])]} />
      <Section title={`${data?.length ?? 0} incidents`}>
        <DataTable rows={data} onRowClick={(r) => navigate(`/incidents/${r.incident_id}`)} columns={[
          { key: "incident_code", title: "Incident", render: (r) => <Text fw={600} size="sm">{r.incident_code}</Text> },
          { key: "incident_type", title: "Type", render: (r) => label(r.incident_type) },
          { key: "where", title: "Where", render: (r) => (r.shipment_id ? code.shipment(r.shipment_id) : r.facility_name) },
          { key: "detection_source", title: "Source", render: (r) => label(r.detection_source) },
          { key: "peak_temperature", title: "Peak °C", align: "right" },
          { key: "exposure_seconds", title: "Exposure", align: "right", render: (r) => fmtDuration(r.exposure_seconds) },
          { key: "affected_batches", title: "Batches", align: "right" },
          { key: "severity", title: "Severity", render: (r) => <StatusBadge value={r.severity} /> },
          { key: "incident_status", title: "Status", render: (r) => <StatusBadge value={r.incident_status} /> },
          { key: "detected_at", title: "Detected" },
        ]} />
      </Section>
      <ReportIncident opened={opened} onClose={close} onCreated={(id) => navigate(`/incidents/${id}`)} />
    </Stack>
  );
}

function ReportIncident({ opened, onClose, onCreated }: { opened: boolean; onClose: () => void; onCreated: (id: number) => void }) {
  const shipments = useApi<any[]>(opened ? "/shipments" : null).data ?? [];
  const facilities = useApi<any[]>(opened ? "/facilities" : null).data ?? [];
  const form = useForm({
    initialValues: { target: "shipment", shipment_id: "", facility_id: "", incident_type: "other", severity: "medium",
                     start_time: "", description: "" },
    validate: {
      shipment_id: (v, a) => (a.target === "shipment" && !v ? "Pick the shipment" : null),
      facility_id: (v, a) => (a.target === "facility" && !v ? "Pick the facility" : null),
      description: (v) => (v.trim().length >= 5 ? null : "Describe what happened (at least 5 characters)"),
    },
  });
  const create = useAction("POST", () => "/incidents", "Incident reported", (row) => { form.reset(); onClose(); onCreated(row.incident_id); });
  const v = form.values;
  return (
    <Modal opened={opened} onClose={onClose} title="Report incident" size="lg">
      <form onSubmit={form.onSubmit((x) => create.mutate({
        incident_type: x.incident_type, severity: x.severity, description: x.description,
        shipment_id: x.target === "shipment" ? Number(x.shipment_id) : null,
        facility_id: x.target === "facility" ? Number(x.facility_id) : null,
        start_time: x.start_time ? new Date(x.start_time).toISOString() : null,
      }))}>
        <Stack>
          <SegmentedControl data={[{ value: "shipment", label: "Shipment" }, { value: "facility", label: "Facility" }]}
            {...form.getInputProps("target")} />
          {v.target === "shipment"
            ? <Select label="Shipment" searchable {...form.getInputProps("shipment_id")}
                data={shipments.map((s) => ({ value: String(s.shipment_id),
                  label: `${code.shipment(s.shipment_id)} · ${s.origin_name} → ${s.destination_name}` }))} />
            : <Select label="Facility" {...form.getInputProps("facility_id")}
                data={facilities.map((f) => ({ value: String(f.facility_id), label: f.facility_name }))} />}
          <Group grow>
            <Select label="Type" data={opts(["temperature_excursion", "humidity_excursion", "sensor_failure", "other"])}
              {...form.getInputProps("incident_type")} />
            <Select label="Severity" data={opts(["low", "medium", "high", "critical"])} {...form.getInputProps("severity")} />
          </Group>
          <TextInput type="datetime-local" label="Started (if known)" {...form.getInputProps("start_time")} />
          <Textarea label="Description" minRows={3} {...form.getInputProps("description")} />
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>Cancel</Button>
            <Button type="submit" loading={create.isPending}>Report</Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
