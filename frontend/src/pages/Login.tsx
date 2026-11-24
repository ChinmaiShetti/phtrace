import { IconArrowRight, IconCheck, IconFingerprint } from "@tabler/icons-react";
import { Brand, ThermalField } from "../Identity";
import { Alert, Button, PasswordInput, Stack, Text, TextInput } from "@mantine/core";
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
    <main className="login-layout">
      <section className="login-art">
        <Brand />
        <div className="login-title">
          <h1>Cold-chain<br /><em>traceability.</em></h1>
          <p>Track shipments, monitor temperature excursions, and trace every affected batch.</p>
        </div>
        <ThermalField />
        <div className="chain-steps" aria-hidden="true"><span>Dispatch</span><i /><span>Transit</span><i /><span>Receipt</span></div>
      </section>
      <section className="login-panel">
        <div className="login-form">
          <IconFingerprint className="login-symbol" size={34} stroke={1.4} />
          <h2>Staff sign in</h2>
          <Text c="dimmed" mb="xl">Access your PharmaTrace workspace.</Text>
          <form onSubmit={submit}>
            <Stack gap="md">
              <TextInput label="Email" type="email" autoComplete="username" placeholder="you@pharmatrace.local" {...form.getInputProps("email")} />
              <PasswordInput label="Password" autoComplete="current-password" {...form.getInputProps("password")} />
              {error && <Alert color="red" role="alert">{error}</Alert>}
              <Button type="submit" loading={busy} fullWidth size="md" rightSection={<IconArrowRight size={17} />}>Sign in</Button>
            </Stack>
          </form>
          <fieldset className="demo-accounts">
            <legend>Demo accounts</legend>
            <Text size="sm" c="dimmed" mb="sm">Choose a role to fill in its credentials.</Text>
            <div className="demo-grid">{DEMO.map(([role, email, pw]) => (
              <button type="button" key={email} aria-pressed={form.values.email === email && form.values.password === pw}
                onClick={() => { form.setValues({ email, password: pw }); form.clearErrors(); setError(null); }}>
                {role}{form.values.email === email && form.values.password === pw && <IconCheck size={14} />}
              </button>
            ))}</div>
          </fieldset>
        </div>
      </section>
    </main>
  );
}
