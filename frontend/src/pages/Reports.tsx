import { Stack, Tabs, Text } from "@mantine/core";
import { useState } from "react";
import { useApi } from "../api";
import { DataTable, label, PageHeader, Section, StatusBadge } from "../ui";

const BADGES = new Set(["severity", "batch_status", "action_status", "refrigeration_status", "installation_status"]);

export default function ReportsPage() {
  const reports = useApi<{ key: string; title: string }[]>("/reports").data ?? [];
  const [active, setActive] = useState<string | null>("incidents-by-type");
  const { data } = useApi<{ title: string; rows: any[] }>(active ? `/reports/${active}` : null);
  const columns = Object.keys(data?.rows?.[0] ?? {}).map((k) => ({
    key: k, title: label(k), render: BADGES.has(k) ? (r: any) => <StatusBadge value={r[k]} /> : undefined,
  }));
  return (
    <Stack>
      <PageHeader title="Reports" subtitle="Each report is a SQL view; the same query can be run in psql." />
      <Tabs value={active} onChange={setActive}>
        <Tabs.List>
          {reports.map((r) => <Tabs.Tab key={r.key} value={r.key}>{r.title}</Tabs.Tab>)}
        </Tabs.List>
      </Tabs>
      <Section title={data?.title ?? ""}>
        {data && data.rows.length === 0 ? <Text c="dimmed" size="sm">No rows: nothing to report.</Text>
          : <DataTable rows={data?.rows} columns={columns} />}
      </Section>
    </Stack>
  );
}
