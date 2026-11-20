import { Button, Code, Group, Modal, Select, Stack, Tabs, TagsInput, TextInput } from "@mantine/core";
import { useForm } from "@mantine/form";
import { useDisclosure } from "@mantine/hooks";
import { IconPlus } from "@tabler/icons-react";
import { useState } from "react";
import { useAction, useApi } from "../api";
import { useAuth } from "../auth";
import { code, DataTable, fmtTime, label, opts, PageHeader, Section, StatusBadge } from "../ui";

export default function AdminPage() {
  const { can } = useAuth();
  return (
    <Stack>
      <PageHeader title="Facilities & admin" subtitle="Master data, sensor deployment, staff accounts and the audit trail." />
      <Tabs defaultValue="facilities">
        <Tabs.List mb="md">
          <Tabs.Tab value="facilities">Facilities</Tabs.Tab>
          <Tabs.Tab value="vehicles">Vehicles</Tabs.Tab>
          <Tabs.Tab value="sensors">Sensors</Tabs.Tab>
          <Tabs.Tab value="staff">Staff</Tabs.Tab>
          {can("quality_manager", "admin") && <Tabs.Tab value="audit">Audit log</Tabs.Tab>}
        </Tabs.List>
        <Tabs.Panel value="facilities"><Facilities /></Tabs.Panel>
        <Tabs.Panel value="vehicles"><Vehicles /></Tabs.Panel>
        <Tabs.Panel value="sensors"><Sensors /></Tabs.Panel>
        <Tabs.Panel value="staff"><Staff /></Tabs.Panel>
        {can("quality_manager", "admin") && <Tabs.Panel value="audit"><Audit /></Tabs.Panel>}
      </Tabs>
    </Stack>
  );
}

const editor = ["operator", "quality_manager", "admin"] as const;

function Facilities() {
  const { data } = useApi<any[]>("/facilities");
  const { can } = useAuth();
  const [opened, { open, close }] = useDisclosure();
  const form = useForm({
    initialValues: { facility_name: "", facility_type: "warehouse", street: "", city: "", pincode: "", phone_numbers: [] as string[] },
    validate: {
      facility_name: (v) => (v.trim().length >= 2 ? null : "Required"),
      street: (v) => (v.trim().length >= 2 ? null : "Required"),
      city: (v) => (v.trim().length >= 2 ? null : "Required"),
      pincode: (v) => (/^[1-9][0-9]{5}$/.test(v) ? null : "Six digits, not starting with 0"),
      phone_numbers: (v) => (v.every((p) => /^[0-9+ -]{6,20}$/.test(p)) ? null : "Digits, spaces, + or - only"),
    },
  });
  const create = useAction("POST", () => "/facilities", "Facility added", () => { form.reset(); close(); });
  return (
    <Section title="Facilities" actions={can(...editor) && <Button size="xs" leftSection={<IconPlus size={14} />} onClick={open}>Add</Button>}>
      <DataTable rows={data} columns={[
        { key: "facility_name", title: "Name" },
        { key: "facility_type", title: "Type", render: (r) => label(r.facility_type) },
        { key: "address", title: "Address", render: (r) => `${r.street}, ${r.city} ${r.pincode}` },
        { key: "phone_numbers", title: "Phones" },
      ]} />
      <Modal opened={opened} onClose={close} title="Add facility">
        <form onSubmit={form.onSubmit((v) => create.mutate(v))}>
          <Stack>
            <TextInput label="Name" {...form.getInputProps("facility_name")} />
            <Select label="Type" data={opts(["warehouse", "distribution_centre", "hospital", "clinic", "pharmacy"])}
              {...form.getInputProps("facility_type")} />
            <TextInput label="Street" {...form.getInputProps("street")} />
            <Group grow>
              <TextInput label="City" {...form.getInputProps("city")} />
              <TextInput label="PIN code" {...form.getInputProps("pincode")} />
            </Group>
            <TagsInput label="Phone numbers" description="Press Enter after each number" {...form.getInputProps("phone_numbers")} />
            <Button type="submit" loading={create.isPending}>Save</Button>
          </Stack>
        </form>
      </Modal>
    </Section>
  );
}

function Vehicles() {
  const { data } = useApi<any[]>("/vehicles");
  const { can } = useAuth();
  const [reg, setReg] = useState("");
  const [type, setType] = useState<string | null>("refrigerated_van");
  const create = useAction("POST", () => "/vehicles", "Vehicle added", () => setReg(""));
  const update = useAction<{ id: number; body: any }>("PATCH", (v) => `/vehicles/${v.id}`, "Vehicle updated");
  return (
    <Section title="Vehicles">
      {can(...editor) && (
        <Group align="flex-end" mb="md">
          <TextInput label="Registration" placeholder="KA01AB1234" value={reg} onChange={(e) => setReg(e.target.value.toUpperCase())} />
          <Select label="Type" value={type} onChange={setType} data={opts(["refrigerated_van", "refrigerated_truck", "insulated_van"])} />
          <Button disabled={!reg} loading={create.isPending} onClick={() => create.mutate({ registration_number: reg, vehicle_type: type })}>Add</Button>
        </Group>
      )}
      <DataTable rows={data} columns={[
        { key: "registration_number", title: "Registration" },
        { key: "vehicle_type", title: "Type", render: (r) => label(r.vehicle_type) },
        { key: "active_shipments", title: "On the road", align: "right" },
        { key: "refrigeration_status", title: "Refrigeration", render: (r) => can(...editor)
          ? <Select size="xs" w={150} value={r.refrigeration_status} allowDeselect={false} data={opts(["operational", "degraded", "faulty"])}
              onChange={(v) => v && update.mutate({ id: r.vehicle_id, body: { refrigeration_status: v } })} />
          : <StatusBadge value={r.refrigeration_status} /> },
      ]} />
    </Section>
  );
}

function Sensors() {
  const { data } = useApi<any[]>("/sensors");
  const facilities = useApi<any[]>("/facilities").data ?? [];
  const { can } = useAuth();
  const [serial, setSerial] = useState("");
  const [stype, setStype] = useState<string | null>("temperature");
  const [assignFor, setAssignFor] = useState<any | null>(null);
  const [facility, setFacility] = useState<string | null>(null);
  const create = useAction("POST", () => "/sensors", "Sensor registered", () => setSerial(""));
  const status = useAction<{ id: number; body: any }>("PATCH", (v) => `/sensors/${v.id}`, "Sensor updated");
  const end = useAction<{ id: number }>("POST", (v) => `/sensor-assignments/${v.id}/end`, "Sensor detached");
  const assign = useAction("POST", () => "/sensor-assignments", "Sensor installed at facility", () => setAssignFor(null));
  return (
    <Section title="Sensors">
      {can(...editor) && (
        <Group align="flex-end" mb="md">
          <TextInput label="Serial number" placeholder="TL-1011" value={serial} onChange={(e) => setSerial(e.target.value)} />
          <Select label="Type" value={stype} onChange={setStype} data={opts(["temperature", "humidity", "temp_humidity"])} />
          <Button disabled={serial.length < 3} loading={create.isPending} onClick={() => create.mutate({ serial_number: serial, sensor_type: stype })}>Register</Button>
        </Group>
      )}
      <DataTable rows={data} columns={[
        { key: "serial_number", title: "Serial" },
        { key: "sensor_type", title: "Type", render: (r) => label(r.sensor_type) },
        { key: "where", title: "Attached to", render: (r) => r.shipment_id ? code.shipment(r.shipment_id) : r.facility_name ?? "—" },
        { key: "last_reading", title: "Last reading", render: (r) => fmtTime(r.last_reading) },
        { key: "installation_status", title: "Status", render: (r) => can(...editor)
          ? <Select size="xs" w={120} value={r.installation_status} allowDeselect={false} data={opts(["active", "inactive", "faulty"])}
              onChange={(v) => v && status.mutate({ id: r.sensor_id, body: { installation_status: v } })} />
          : <StatusBadge value={r.installation_status} /> },
        { key: "act", title: "", render: (r) => !can(...editor) ? null : r.assignment_id
          ? <Button size="compact-xs" variant="subtle" color="red" onClick={() => end.mutate({ id: r.assignment_id })}>Detach</Button>
          : r.installation_status === "active" && <Button size="compact-xs" variant="subtle" onClick={() => setAssignFor(r)}>Install at facility</Button> },
      ]} />
      <Modal opened={!!assignFor} onClose={() => setAssignFor(null)} title={`Install ${assignFor?.serial_number}`}>
        <Stack>
          <Select label="Facility" value={facility} onChange={setFacility}
            data={facilities.map((f) => ({ value: String(f.facility_id), label: f.facility_name }))} />
          <Button disabled={!facility} onClick={() => assign.mutate({ sensor_id: assignFor.sensor_id, facility_id: Number(facility) })}>Install</Button>
        </Stack>
      </Modal>
    </Section>
  );
}

function Staff() {
  const { data } = useApi<any[]>("/staff");
  const { can } = useAuth();
  const [opened, { open, close }] = useDisclosure();
  const update = useAction<{ id: number; body: any }>("PATCH", (v) => `/staff/${v.id}`, "Account updated");
  const form = useForm({
    initialValues: { staff_name: "", email: "", password: "", role: "operator" },
    validate: {
      staff_name: (v) => (v.trim().length >= 2 ? null : "Required"),
      email: (v) => (/^\S+@\S+\.\S+$/.test(v) ? null : "Enter a valid email"),
      password: (v) => (v.length >= 8 ? null : "At least 8 characters"),
    },
  });
  const create = useAction("POST", () => "/staff", "Account created", () => { form.reset(); close(); });
  const admin = can("admin");
  return (
    <Section title="Staff" actions={admin && <Button size="xs" leftSection={<IconPlus size={14} />} onClick={open}>Add</Button>}>
      <DataTable rows={data} columns={[
        { key: "staff_name", title: "Name" },
        { key: "email", title: "Email" },
        { key: "role", title: "Role", render: (r) => admin
          ? <Select size="xs" w={170} value={r.role} allowDeselect={false} data={opts(["operator", "investigator", "quality_manager", "admin"])}
              onChange={(v) => v && update.mutate({ id: r.staff_id, body: { role: v } })} />
          : label(r.role) },
        { key: "account_status", title: "Account", render: (r) => admin
          ? <Select size="xs" w={110} value={r.account_status} allowDeselect={false} data={opts(["active", "inactive"])}
              onChange={(v) => v && update.mutate({ id: r.staff_id, body: { account_status: v } })} />
          : <StatusBadge value={r.account_status} /> },
      ]} />
      <Modal opened={opened} onClose={close} title="New staff account">
        <form onSubmit={form.onSubmit((v) => create.mutate(v))}>
          <Stack>
            <TextInput label="Name" {...form.getInputProps("staff_name")} />
            <TextInput label="Email" {...form.getInputProps("email")} />
            <TextInput label="Initial password" type="password" {...form.getInputProps("password")} />
            <Select label="Role" data={opts(["operator", "investigator", "quality_manager", "admin"])} {...form.getInputProps("role")} />
            <Button type="submit" loading={create.isPending}>Create</Button>
          </Stack>
        </form>
      </Modal>
    </Section>
  );
}

function Audit() {
  const [table, setTable] = useState<string | null>(null);
  const { data } = useApi<any[]>(`/audit${table ? `?table=${table}` : ""}`);
  return (
    <Section title="Audit log" actions={<Select size="xs" placeholder="All tables" clearable value={table} onChange={setTable}
      data={["batch", "shipment", "incident", "incident_batch", "investigation", "corrective_action", "sensor_reading", "staff"]} />}>
      <DataTable rows={data} rowKey={(r) => r.audit_id} columns={[
        { key: "changed_at", title: "When" },
        { key: "staff_name", title: "By", render: (r) => r.staff_name ?? "system" },
        { key: "table_name", title: "Table" },
        { key: "row_pk", title: "Row" },
        { key: "action", title: "Action" },
        { key: "reason", title: "Reason" },
        { key: "diff", title: "Changed", render: (r) => <Code fz="xs">{diffText(r.old_data, r.new_data)}</Code> },
      ]} />
    </Section>
  );
}

function diffText(oldData: any, newData: any) {
  if (!oldData) return "created";
  if (!newData) return "deleted";
  return Object.keys(newData).filter((k) => JSON.stringify(oldData[k]) !== JSON.stringify(newData[k]))
    .map((k) => `${k}: ${oldData[k]} → ${newData[k]}`).join("; ");
}
