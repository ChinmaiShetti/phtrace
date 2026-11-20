import { Button, Group, Modal, NumberInput, Select, Stack, Switch, TextInput } from "@mantine/core";
import { useForm } from "@mantine/form";
import { useDisclosure } from "@mantine/hooks";
import { IconPlus } from "@tabler/icons-react";
import { useAction, useApi } from "../api";
import { useAuth } from "../auth";
import { DataTable, label, opts, PageHeader, Section } from "../ui";

export default function ProductsPage() {
  const { data } = useApi<any[]>("/products");
  const { can } = useAuth();
  const [opened, { open, close }] = useDisclosure();
  return (
    <Stack>
      <PageHeader title="Products" subtitle="Configured monitoring limits are illustrative, not real product specifications."
        actions={can("operator", "quality_manager", "admin") &&
          <Button leftSection={<IconPlus size={16} />} onClick={open}>Register product</Button>} />
      <Section title={`${data?.length ?? 0} products`}>
        <DataTable rows={data} columns={[
          { key: "product_name", title: "Product" },
          { key: "product_type", title: "Type", render: (r) => label(r.product_type) },
          { key: "temp", title: "Temperature", render: (r) => `${r.min_temp} to ${r.max_temp} °C` },
          { key: "hum", title: "Humidity", render: (r) => (r.min_humidity == null ? "—" : `${r.min_humidity} to ${r.max_humidity} %`) },
          { key: "batches", title: "Batches", align: "right" },
        ]} />
      </Section>
      <NewProduct opened={opened} onClose={close} />
    </Stack>
  );
}

function NewProduct({ opened, onClose }: { opened: boolean; onClose: () => void }) {
  const form = useForm({
    initialValues: { product_name: "", product_type: "vaccine", min_temp: 2 as number | string, max_temp: 8 as number | string,
                     humidity: false, min_humidity: 30 as number | string, max_humidity: 65 as number | string },
    validate: {
      product_name: (v) => (v.trim().length >= 2 ? null : "Name is required"),
      max_temp: (v, all) => (Number(v) > Number(all.min_temp) ? null : "Maximum must be above minimum"),
      max_humidity: (v, all) => (!all.humidity || Number(v) > Number(all.min_humidity) ? null : "Maximum must be above minimum"),
    },
  });
  const create = useAction("POST", () => "/products", "Product registered", () => { form.reset(); onClose(); });
  return (
    <Modal opened={opened} onClose={onClose} title="Register product">
      <form onSubmit={form.onSubmit((v) => create.mutate({
        product_name: v.product_name, product_type: v.product_type, min_temp: Number(v.min_temp), max_temp: Number(v.max_temp),
        min_humidity: v.humidity ? Number(v.min_humidity) : null, max_humidity: v.humidity ? Number(v.max_humidity) : null,
      }))}>
        <Stack>
          <TextInput label="Product name" {...form.getInputProps("product_name")} />
          <Select label="Type" data={opts(["vaccine", "biologic", "medicine", "other"])} {...form.getInputProps("product_type")} />
          <Group grow>
            <NumberInput label="Min °C" step={0.5} {...form.getInputProps("min_temp")} />
            <NumberInput label="Max °C" step={0.5} {...form.getInputProps("max_temp")} />
          </Group>
          <Switch label="Humidity-sensitive" {...form.getInputProps("humidity", { type: "checkbox" })} />
          {form.values.humidity && (
            <Group grow>
              <NumberInput label="Min % RH" min={0} max={100} {...form.getInputProps("min_humidity")} />
              <NumberInput label="Max % RH" min={0} max={100} {...form.getInputProps("max_humidity")} />
            </Group>
          )}
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>Cancel</Button>
            <Button type="submit" loading={create.isPending}>Save</Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
