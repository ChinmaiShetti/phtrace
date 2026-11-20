import { Alert, Badge, Card, Group, Loader, Table, Text, Title, type MantineColor } from "@mantine/core";
import type { ReactNode } from "react";

export const code = {
  shipment: (id: number) => `SH${String(id).padStart(3, "0")}`,
  incident: (id: number) => `INC${String(id).padStart(4, "0")}`,
};

export const label = (s: string | null | undefined) =>
  s ? s.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase()) : "—";

export function fmtTime(v: string | null | undefined) {
  if (!v) return "—";
  return new Date(v).toLocaleString(undefined, { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

/** Duration for exposure figures: seconds under a minute, minutes under a day. */
export function fmtDuration(seconds: number | null | undefined) {
  if (seconds == null) return "—";
  if (seconds < 60) return `${seconds} s`;
  if (seconds < 86400) return `${Math.round(seconds / 60)} min`;
  return `${(seconds / 86400).toFixed(1)} days`;
}

export function fmtDate(v: string | null | undefined) {
  if (!v) return "—";
  return new Date(v).toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" });
}

const COLORS: Record<string, MantineColor> = {
  // shipments
  planned: "gray", in_transit: "blue", delivered: "teal", cancelled: "dark",
  // batches
  available: "teal", on_hold: "orange", quarantined: "red", released: "green", returned: "grape", disposed: "dark",
  // incidents and work items
  open: "red", investigating: "orange", resolved: "blue", closed: "gray",
  assigned: "gray", in_progress: "blue", completed: "teal", pending: "yellow",
  pending_review: "yellow", under_assessment: "orange", assessed: "teal",
  // severity
  low: "yellow", medium: "orange", high: "red", critical: "grape",
  // readings and devices
  valid: "teal", suspicious: "orange", invalid: "red",
  active: "teal", inactive: "gray", faulty: "red", operational: "teal", degraded: "orange",
};

export function StatusBadge({ value }: { value: string | null | undefined }) {
  if (!value) return <Text c="dimmed">—</Text>;
  return (
    <Badge color={COLORS[value] ?? "gray"} variant="light" radius="sm">
      {label(value)}
    </Badge>
  );
}

export interface Column<T> {
  key: string;
  title: string;
  render?: (row: T) => ReactNode;
  align?: "left" | "right" | "center";
}

export function DataTable<T extends Record<string, any>>({
  rows, columns, onRowClick, empty = "Nothing to show yet.", rowKey, minWidth = 0,
}: {
  minWidth?: number;
  rows: T[] | undefined;
  columns: Column<T>[];
  onRowClick?: (row: T) => void;
  empty?: string;
  rowKey?: (row: T, i: number) => string | number;
}) {
  if (!rows) return <Loader size="sm" />;
  if (rows.length === 0) return <Text c="dimmed" size="sm">{empty}</Text>;
  return (
    <Table.ScrollContainer minWidth={minWidth}>
      <Table striped highlightOnHover={!!onRowClick} verticalSpacing="xs" fz="sm">
        <Table.Thead>
          <Table.Tr>
            {columns.map((c) => (
              <Table.Th key={c.key} ta={c.align}>{c.title}</Table.Th>
            ))}
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {rows.map((r, i) => (
            <Table.Tr key={rowKey ? rowKey(r, i) : i} onClick={onRowClick ? () => onRowClick(r) : undefined}
              style={onRowClick ? { cursor: "pointer" } : undefined}>
              {columns.map((c) => (
                <Table.Td key={c.key} ta={c.align}>
                  {c.render ? c.render(r) : formatCell(r[c.key])}
                </Table.Td>
              ))}
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}

function formatCell(v: unknown): ReactNode {
  if (v === null || v === undefined) return "—";
  if (typeof v === "boolean") return v ? "Yes" : "No";
  if (typeof v === "string" && /^\d{4}-\d{2}-\d{2}T/.test(v)) return fmtTime(v);
  if (Array.isArray(v)) return v.join(", ");
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: ReactNode; actions?: ReactNode }) {
  return (
    <Group justify="space-between" align="flex-end" mb="lg">
      <div>
        <Title order={2}>{title}</Title>
        {subtitle && <Text component="div" c="dimmed" size="sm" mt={4}>{subtitle}</Text>}
      </div>
      {actions && <Group gap="xs">{actions}</Group>}
    </Group>
  );
}

export function Section({ title, children, actions }: { title: string; children: ReactNode; actions?: ReactNode }) {
  return (
    <Card withBorder radius="md" padding="lg">
      <Group justify="space-between" mb="sm">
        <Title order={4}>{title}</Title>
        {actions && <Group gap="xs">{actions}</Group>}
      </Group>
      {children}
    </Card>
  );
}

export function ErrorNote({ error }: { error: unknown }) {
  if (!error) return null;
  return <Alert color="red" variant="light">{(error as Error).message}</Alert>;
}

/** Readable list of options for Select components. */
export const opts = (values: string[]) => values.map((v) => ({ value: v, label: label(v) }));
