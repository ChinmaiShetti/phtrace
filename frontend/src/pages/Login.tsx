import { Alert, Anchor, Button, Card, Center, PasswordInput, Stack, Table, Text, TextInput, Title } from "@mantine/core";
import { useForm } from "@mantine/form";
import { useState } from "react";
import { useAuth } from "../auth";

const DEMO = [
  ["Operator", "operator@pharmatrace.local", "operator123"],
  ["Investigator", "investigator@pharmatrace.local", "investigator123"],
  ["Quality manager", "qm@pharmatrace.local", "qm123"],
  ["Administrator", "admin@pharmatrace.local", "admin123"],
];

export default function LoginPage() {
  const { login } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const form = useForm({
    initialValues: { email: "", password: "" },
    validate: {
      email: (v) => (/^\S+@\S+\.\S+$/.test(v) ? null : "Enter a valid email address"),
      password: (v) => (v.length > 0 ? null : "Password is required"),
    },
  });

  const submit = form.onSubmit(async ({ email, password }) => {
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  });

  return (
    <Center mih="100vh" p="md">
      <Stack w={420} gap="md">
        <div>
          <Title order={1}>Pharma<Text span c="cyan" inherit>Trace</Text></Title>
          <Text c="dimmed">Cold-chain integrity, traceability and incident management</Text>
        </div>
        <Card withBorder padding="xl" radius="md">
          <form onSubmit={submit}>
            <Stack>
              <TextInput label="Email" placeholder="you@pharmatrace.local" {...form.getInputProps("email")} />
              <PasswordInput label="Password" {...form.getInputProps("password")} />
              {error && <Alert color="red" variant="light">{error}</Alert>}
              <Button type="submit" loading={busy} fullWidth>Sign in</Button>
            </Stack>
          </form>
        </Card>
        <Card withBorder padding="md" radius="md">
          <Text size="sm" fw={600} mb={4}>Demo accounts</Text>
          <Table fz="xs">
            <Table.Tbody>
              {DEMO.map(([role, email, pw]) => (
                <Table.Tr key={email}>
                  <Table.Td>{role}</Table.Td>
                  <Table.Td>
                    <Anchor size="xs" onClick={() => form.setValues({ email, password: pw })}>{email}</Anchor>
                  </Table.Td>
                  <Table.Td><Text size="xs" ff="monospace">{pw}</Text></Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>
      </Stack>
    </Center>
  );
}
