import { ActionIcon, Button, Group, Modal, NumberInput, SegmentedControl, Select, Stack, Text, TextInput } from "@mantine/core";
import { useForm } from "@mantine/form";
import { useDisclosure } from "@mantine/hooks";
import { IconPlus, IconTrash } from "@tabler/icons-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAction, useApi } from "../api";
import { useAuth } from "../auth";
import { code, DataTable, fmtTime, PageHeader, Section, StatusBadge } from "../ui";

export default function ShipmentsPage() {
  const [status, setStatus] = useState("all");
  const { data } = useApi<any[]>(status === "all" ? "/shipments" : `/shipments?status=${status}`);
  const navigate = useNavigate();
  const { can } = useAuth();
  const [opened, { open, close }] = useDisclosure();

  return (
    <Stack>
      <PageHeader title="Shipments" subtitle="Create a shipment, load batches, then dispatch it as one database transaction."
        actions={can("operator", "quality_manager", "admin") &&
          <Button leftSection={<IconPlus size={16} />} onClick={open}>New shipment</Button>} />
      <SegmentedControl value={status} onChange={setStatus} w="fit-content"
        data={[{ value: "all", label: "All" }, { value: "planned", label: "Planned" },
               { value: "in_transit", label: "In transit" }, { value: "delivered", label: "Delivered" }]} />
      <Section title={`${data?.length ?? 0} shipments`}>
        <DataTable rows={data} onRowClick={(r) => navigate(`/shipments/${r.shipment_id}`)} columns={[
          { key: "id", title: "Shipment", render: (r) => <Text span fw={600} size="sm">{code.shipment(r.shipment_id)}</Text> },
          { key: "origin_name", title: "From" },
          { key: "destination_name", title: "To" },
          { key: "registration_number", title: "Vehicle" },
          { key: "batch_lines", title: "Batches", align: "right" },
          { key: "units", title: "Units", align: "right" },
          { key: "dispatch_time", title: "Dispatched" },
          { key: "expected_arrival", title: "Expected", render: (r) =>
            <Text size="sm" c={r.overdue ? "red" : undefined}>{fmtTime(r.expected_arrival)}</Text> },
          { key: "shipment_status", title: "Status", render: (r) => <StatusBadge value={r.shipment_status} /> },
        ]} />
      </Section>
      <NewShipment opened={opened} onClose={close} onCreated={(id) => navigate(`/shipments/${id}`)} />
    </Stack>
  );
}

function NewShipment({ opened, onClose, onCreated }: { opened: boolean; onClose: () => void; onCreated: (id: number) => void }) {
  const vehicles = useApi<any[]>(opened ? "/vehicles" : null).data ?? [];
  const facilities = useApi<any[]>(opened ? "/facilities" : null).data ?? [];
  const sensors = useApi<any[]>(opened ? "/sensors" : null).data ?? [];
  const batches = useApi<any[]>(opened ? "/batches" : null).data ?? [];

  const form = useForm({
    initialValues: {
      vehicle_id: "", origin_facility_id: "", destination_facility_id: "", expected_arrival: "", sensor_id: "",
      lines: [{ batch_id: "", quantity_shipped: 100 as number | string }],
    },
    validate: {
      vehicle_id: (v) => (v ? null : "Vehicle is required"),
      origin_facility_id: (v) => (v ? null : "Origin is required"),
      destination_facility_id: (v, all) =>
        !v ? "Destination is required" : v === all.origin_facility_id ? "Destination must differ from origin" : null,
      expected_arrival: (v) => (!v ? "Expected arrival is required"
        : new Date(v) <= new Date() ? "Expected arrival must be in the future" : null),
      lines: { batch_id: (v) => (v ? null : "Pick a batch"),
               quantity_shipped: (v) => (Number(v) > 0 ? null : "Quantity must be positive") },
    },
  });

  const create = useAction("POST", () => "/shipments", "Shipment created", (row) => {
    form.reset();
    onClose();
    onCreated(row.shipment_id);
  });

  const submit = form.onSubmit((v) => create.mutate({
    vehicle_id: Number(v.vehicle_id), origin_facility_id: Number(v.origin_facility_id),
    destination_facility_id: Number(v.destination_facility_id),
    expected_arrival: new Date(v.expected_arrival).toISOString(),
    sensor_id: v.sensor_id ? Number(v.sensor_id) : null,
    lines: v.lines.map((l) => ({ batch_id: Number(l.batch_id), quantity_shipped: Number(l.quantity_shipped) })),
  }));

  const facilityOpts = facilities.map((f) => ({ value: String(f.facility_id), label: f.facility_name }));
  const freeSensors = sensors.filter((s) => s.installation_status === "active" && !s.assignment_id);

  return (
    <Modal opened={opened} onClose={onClose} title="New shipment" size="lg">
      <form onSubmit={submit}>
        <Stack>
          <Group grow>
            <Select label="Origin" data={facilityOpts} searchable {...form.getInputProps("origin_facility_id")} />
            <Select label="Destination" data={facilityOpts} searchable {...form.getInputProps("destination_facility_id")} />
          </Group>
          <Group grow>
            <Select label="Vehicle" {...form.getInputProps("vehicle_id")}
              data={vehicles.map((v) => ({ value: String(v.vehicle_id),
                label: `${v.registration_number} (${v.refrigeration_status})` }))} />
            <TextInput type="datetime-local" label="Expected arrival" {...form.getInputProps("expected_arrival")} />
          </Group>
          <Select label="Monitoring sensor" description="Needed before dispatch" clearable
            data={freeSensors.map((s) => ({ value: String(s.sensor_id), label: `${s.serial_number} (${s.sensor_type})` }))}
            {...form.getInputProps("sensor_id")} />
          <Text fw={600} size="sm">Batches</Text>
          {form.values.lines.map((_, i) => (
            <Group key={i} align="flex-start">
              <Select style={{ flex: 1 }} placeholder="Batch" searchable {...form.getInputProps(`lines.${i}.batch_id`)}
                data={batches.filter((b) => ["available", "released"].includes(b.batch_status) && !b.is_expired)
                  .map((b) => ({ value: String(b.batch_id),
                    label: `${b.batch_number} · ${b.product_name} · ${b.on_hand} on hand` }))} />
              <NumberInput w={120} min={1} {...form.getInputProps(`lines.${i}.quantity_shipped`)} />
              <ActionIcon variant="subtle" color="red" mt={4} disabled={form.values.lines.length === 1}
                onClick={() => form.removeListItem("lines", i)} aria-label="Remove line"><IconTrash size={16} /></ActionIcon>
            </Group>
          ))}
          <Button variant="light" size="xs" w="fit-content" leftSection={<IconPlus size={14} />}
            onClick={() => form.insertListItem("lines", { batch_id: "", quantity_shipped: 100 })}>Add batch</Button>
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>Cancel</Button>
            <Button type="submit" loading={create.isPending}>Create shipment</Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
