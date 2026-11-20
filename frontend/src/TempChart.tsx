import { LineChart } from "@mantine/charts";
import { Text } from "@mantine/core";

interface Point { recorded_at: string; temperature: number | null }

/** Temperature over time with the configured limits drawn as reference lines. */
export function TempChart({ readings, min, max, height = 260 }:
  { readings: Point[]; min?: number | null; max?: number | null; height?: number }) {
  const valid = readings.filter((r) => r.temperature !== null && Math.abs(Number(r.temperature)) < 100);   // hide corrupt values
  const times = valid.map((r) => new Date(r.recorded_at).getTime());
  const short = times.length > 1 && Math.max(...times) - Math.min(...times) < 3 * 3600_000;
  const fmt: Intl.DateTimeFormatOptions = short
    ? { hour: "2-digit", minute: "2-digit", second: "2-digit" }
    : { day: "2-digit", hour: "2-digit", minute: "2-digit" };
  const data = valid
    .map((r) => ({
      time: new Date(r.recorded_at).toLocaleString(undefined, fmt),
      ts: new Date(r.recorded_at).getTime(),
      temperature: Number(r.temperature),
    }))
    .sort((a, b) => a.ts - b.ts);
  if (data.length === 0) return <Text c="dimmed" size="sm">No readings in this window.</Text>;
  const ref = [];
  if (max != null) ref.push({ y: Number(max), label: `Max ${max} °C`, color: "red.6" });
  if (min != null) ref.push({ y: Number(min), label: `Min ${min} °C`, color: "blue.6" });
  const values = data.map((d) => d.temperature).concat(ref.map((r) => r.y));
  return (
    <LineChart h={height} data={data} dataKey="time" curveType="monotone" withDots={data.length < 60}
      series={[{ name: "temperature", label: "Temperature °C", color: "cyan.6" }]}
      referenceLines={ref} unit=" °C" tickLine="none" gridAxis="y"
      yAxisProps={{ domain: [Math.floor(Math.min(...values) - 1), Math.ceil(Math.max(...values) + 1)] }}
      xAxisProps={{ minTickGap: 40 }} />
  );
}
