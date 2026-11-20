import { Button, Group, Modal, NumberInput, Select, Stack, Text, TextInput } from "@mantine/core";
import { useForm } from "@mantine/form";
import { useDebouncedValue, useDisclosure } from "@mantine/hooks";
import { IconPlus, IconSearch } from "@tabler/icons-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAction, useApi } from "../api";
import { useAuth } from "../auth";
import { DataTable, fmtDate, PageHeader, Section, StatusBadge } from "../ui";

export default function BatchesPage() {
  const [q, setQ] = useState("");
  const [debounced] = useDebouncedValue(q, 250);
  const { data } = useApi<any[]>(`/batches${debounced ? `?q=${encodeURIComponent(debounced)}` : ""}`);
  const navigate = useNavigate();
  const { can } = useAuth();
  const [opened, { open, close }] = useDisclosure();

  return (
    <Stack>
      <PageHeader title="Batches" subtitle="Quantities and locations are derived from the movement history, never typed in."
        actions={can("operator", "quality_manager", "admin") &&
          <Button leftSection={<IconPlus size={16} />} onClick={open}>Register batch</Button>} />
      <TextInput leftSection={<IconSearch size={16} />} placeholder="Search batch number or product" w={340}
        value={q} onChange={(e) => setQ(e.target.value)} />
      <Section title={`${data?.length ?? 0} batches`}>
        <DataTable rows={data} onRowClick={(r) => navigate(`/batches/${r.batch_id}`)} columns={[
          { key: "batch_number", title: "Batch", render: (r) => <Text fw={600} size="sm">{r.batch_number}</Text> },
          { key: "product_name", title: "Product" },
          { key: "expiry_date", title: "Expiry", render: (r) => (
            <Text size="sm" c={r.is_expired ? "red" : r.days_to_expiry <= 60 ? "orange" : undefined}>
              {fmtDate(r.expiry_date)}{r.is_expired ? " (expired)" : r.days_to_expiry <= 60 ? ` (${r.days_to_expiry} d)` : ""}
            </Text>) },
          { key: "on_hand", title: "On hand", align: "right" },
          { key: "in_transit", title: "In transit", align: "right" },
          { key: "open_incidents", title: "Open incidents", align: "right" },
          { key: "batch_status", title: "Status", render: (r) => <StatusBadge value={r.batch_status} /> },
        ]} />
      </Section>
      <NewBatch opened={opened} onClose={close} />
    </Stack>
  );
}

function NewBatch({ opened, onClose }: { opened: boolean; onClose: () => void }) {
  const products = useApi<any[]>(opened ? "/products" : null).data ?? [];
  const facilities = useApi<any[]>(opened ? "/facilities" : null).data ?? [];
  const form = useForm({
    initialValues: { batch_number: "", product_id: "", manufacturing_date: "", expiry_date: "",
                     initial_quantity: 1000 as number | string, intake_facility_id: "" },
    validate: {
      batch_number: (v) => (/^[A-Za-z0-9-_/]{2,40}$/.test(v) ? null : "2-40 letters, digits, - _ /"),
      product_id: (v) => (v ? null : "Product is required"),
      manufacturing_date: (v) => (!v ? "Required" : new Date(v) > new Date() ? "Cannot be in the future" : null),
      expiry_date: (v, all) => (!v ? "Required" : v <= all.manufacturing_date ? "Must be after manufacturing date" : null),
      initial_quantity: (v) => (Number(v) > 0 ? null : "Must be positive"),
      intake_facility_id: (v) => (v ? null : "Receiving facility is required"),
    },
  });
  const create = useAction("POST", () => "/batches", "Batch registered and received into stock", () => { form.reset(); onClose(); });
  return (
    <Modal opened={opened} onClose={onClose} title="Register batch">
      <form onSubmit={form.onSubmit((v) => create.mutate({ ...v, product_id: Number(v.product_id),
        intake_facility_id: Number(v.intake_facility_id), initial_quantity: Number(v.initial_quantity) }))}>
        <Stack>
          <TextInput label="Batch number" placeholder="B013" {...form.getInputProps("batch_number")} />
          <Select label="Product" data={products.map((p) => ({ value: String(p.product_id), label: p.product_name }))}
            {...form.getInputProps("product_id")} />
          <Group grow>
            <TextInput type="date" label="Manufactured" {...form.getInputProps("manufacturing_date")} />
            <TextInput type="date" label="Expires" {...form.getInputProps("expiry_date")} />
          </Group>
          <Group grow>
            <NumberInput label="Quantity" min={1} {...form.getInputProps("initial_quantity")} />
            <Select label="Received at" {...form.getInputProps("intake_facility_id")}
              data={facilities.map((f) => ({ value: String(f.facility_id), label: f.facility_name }))} />
          </Group>
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>Cancel</Button>
            <Button type="submit" loading={create.isPending}>Register</Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
