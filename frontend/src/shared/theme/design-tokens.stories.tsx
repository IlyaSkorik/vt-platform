import type { Meta, StoryObj } from "@storybook/react-vite";

/**
 * Design-token documentation.
 *
 * A living reference for the VT Platform token system. Every swatch and sample
 * reads its value from a CSS variable, so this page reflects the *current*
 * tokens (and the active theme) rather than hard-coded copies. Toggle the
 * Storybook theme control to see every token respond.
 */

const meta = {
  title: "Design System/Tokens",
  parameters: {
    layout: "fullscreen",
    a11y: { test: "error" },
  },
  tags: ["autodocs"],
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

// --- Presentational helpers (documentation-only, no app dependency) --------

function Section({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}): React.JSX.Element {
  return (
    <section style={{ marginBottom: "var(--space-12)" }}>
      <h2
        style={{
          font: `var(--font-weight-bold) var(--text-2xl)/1.2 var(--font-family-heading)`,
          color: "var(--text-primary)",
          marginBottom: "var(--space-2)",
        }}
      >
        {title}
      </h2>
      {description ? (
        <p style={{ color: "var(--text-muted)", marginBottom: "var(--space-6)", maxWidth: "60ch" }}>
          {description}
        </p>
      ) : null}
      {children}
    </section>
  );
}

function Grid({ children }: { children: React.ReactNode }): React.JSX.Element {
  return (
    <div
      style={{
        display: "grid",
        gap: "var(--space-4)",
        gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
      }}
    >
      {children}
    </div>
  );
}

function Swatch({ token, label }: { token: string; label?: string }): React.JSX.Element {
  return (
    <div
      style={{
        border: "1px solid var(--border-default)",
        borderRadius: "var(--radius-md)",
        overflow: "hidden",
        background: "var(--surface-primary)",
      }}
    >
      <div style={{ height: 64, background: `var(${token})` }} />
      <div style={{ padding: "var(--space-2)" }}>
        <div style={{ fontSize: "var(--text-sm)", color: "var(--text-primary)" }}>
          {label ?? token}
        </div>
        <code style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>{token}</code>
      </div>
    </div>
  );
}

function Page({ children }: { children: React.ReactNode }): React.JSX.Element {
  return (
    <div
      style={{
        padding: "var(--space-8)",
        background: "var(--background-primary)",
        color: "var(--text-primary)",
        minHeight: "100vh",
        fontFamily: "var(--font-family-body)",
      }}
    >
      {children}
    </div>
  );
}

// --- Data (token name lists; values are read live from CSS) ----------------

const PRIMITIVES = [
  "--violet-700",
  "--violet-500",
  "--violet-400",
  "--violet-300",
  "--mauve-500",
  "--mauve-300",
  "--mauve-200",
  "--mauve-100",
  "--gold-100",
  "--gold-300",
  "--gold-500",
  "--gold-700",
  "--flame-100",
  "--flame-300",
  "--flame-500",
  "--flame-700",
];

const SEMANTIC_SURFACES = [
  "--background-primary",
  "--background-secondary",
  "--background-tertiary",
  "--surface-primary",
  "--surface-secondary",
  "--surface-elevated",
  "--border-default",
];

const SEMANTIC_STATUS = ["--success", "--warning", "--danger", "--info"];

const GRADIENTS = [
  "--gradient-background",
  "--gradient-brand",
  "--gradient-gold",
  "--gradient-flame",
  "--gradient-mauve",
  "--gradient-brand-panel",
];

const SPACING = [
  "--space-1",
  "--space-2",
  "--space-3",
  "--space-4",
  "--space-5",
  "--space-6",
  "--space-8",
  "--space-10",
  "--space-12",
  "--space-16",
];

const RADII = [
  "--radius-xs",
  "--radius-sm",
  "--radius-md",
  "--radius-lg",
  "--radius-xl",
  "--radius-2xl",
];

const SHADOWS = ["--shadow-xs", "--shadow-sm", "--shadow-md", "--shadow-lg", "--shadow-xl"];

const TEXT_SIZES = [
  "--text-xs",
  "--text-sm",
  "--text-md",
  "--text-lg",
  "--text-xl",
  "--text-2xl",
  "--text-3xl",
  "--text-4xl",
];

const DURATIONS = ["--duration-fast", "--duration-normal", "--duration-slow", "--duration-slower"];

// --- Stories ----------------------------------------------------------------

export const Typography: Story = {
  render: () => (
    <Page>
      <Section
        title="Типографика / Typography"
        description="Семейства, начертания и шкала размеров. Заголовки используют --font-family-heading, текст — --font-family-body."
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
          {TEXT_SIZES.map((token) => (
            <div
              key={token}
              style={{ display: "flex", alignItems: "baseline", gap: "var(--space-4)" }}
            >
              <code
                style={{
                  width: 120,
                  flexShrink: 0,
                  fontSize: "var(--text-xs)",
                  color: "var(--text-muted)",
                }}
              >
                {token}
              </code>
              <span style={{ fontSize: `var(${token})`, color: "var(--text-primary)" }}>
                Взлёт талантов — The Rise of Talent
              </span>
            </div>
          ))}
        </div>
        <div style={{ display: "flex", gap: "var(--space-6)", marginTop: "var(--space-6)" }}>
          {[
            ["--font-weight-regular", "Regular"],
            ["--font-weight-medium", "Medium"],
            ["--font-weight-semibold", "Semibold"],
            ["--font-weight-bold", "Bold"],
          ].map(([token, label]) => (
            <div key={token}>
              <div style={{ fontWeight: `var(${token})`, fontSize: "var(--text-lg)" }}>{label}</div>
              <code style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>
                {token}
              </code>
            </div>
          ))}
        </div>
      </Section>
    </Page>
  ),
};

export const Colors: Story = {
  name: "Colors (Primitive)",
  render: () => (
    <Page>
      <Section
        title="Примитивные цвета / Primitive Colors"
        description="Сырые значения бренда. Никогда не используются напрямую в компонентах — только через семантические токены."
      >
        <Grid>
          {PRIMITIVES.map((token) => (
            <Swatch key={token} token={token} />
          ))}
        </Grid>
      </Section>
    </Page>
  ),
};

export const SemanticTokens: Story = {
  render: () => (
    <Page>
      <Section
        title="Семантические токены / Semantic Tokens"
        description="Слой смысла: поверхности, текст, границы, статусы. Компоненты используют только их. Значения меняются вместе с темой."
      >
        <h3 style={{ marginBottom: "var(--space-4)", color: "var(--text-secondary)" }}>Surfaces</h3>
        <Grid>
          {SEMANTIC_SURFACES.map((token) => (
            <Swatch key={token} token={token} />
          ))}
        </Grid>
        <h3 style={{ margin: "var(--space-6) 0 var(--space-4)", color: "var(--text-secondary)" }}>
          Status
        </h3>
        <Grid>
          {SEMANTIC_STATUS.map((token) => (
            <Swatch key={token} token={token} />
          ))}
        </Grid>
      </Section>
    </Page>
  ),
};

export const Gradients: Story = {
  render: () => (
    <Page>
      <Section
        title="Градиенты / Gradients"
        description="Брендовые градиенты собраны из примитивов. Доступны как утилиты Tailwind (bg-gradient-brand и т. д.)."
      >
        <Grid>
          {GRADIENTS.map((token) => (
            <div
              key={token}
              style={{
                borderRadius: "var(--radius-lg)",
                overflow: "hidden",
                border: "1px solid var(--border-default)",
              }}
            >
              <div style={{ height: 96, background: `var(${token})` }} />
              <code
                style={{
                  display: "block",
                  padding: "var(--space-2)",
                  fontSize: "var(--text-xs)",
                  color: "var(--text-muted)",
                  background: "var(--surface-primary)",
                }}
              >
                {token}
              </code>
            </div>
          ))}
        </Grid>
      </Section>
    </Page>
  ),
};

export const Spacing: Story = {
  render: () => (
    <Page>
      <Section
        title="Отступы / Spacing"
        description="8-point шкала на базе 4px. Совпадает с утилитами Tailwind."
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
          {SPACING.map((token) => (
            <div
              key={token}
              style={{ display: "flex", alignItems: "center", gap: "var(--space-4)" }}
            >
              <code style={{ width: 100, fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>
                {token}
              </code>
              <div
                style={{ height: 16, width: `var(${token})`, background: "var(--brand-accent)" }}
              />
            </div>
          ))}
        </div>
      </Section>
    </Page>
  ),
};

export const Radius: Story = {
  render: () => (
    <Page>
      <Section title="Скругления / Radius" description="Шкала радиусов границ.">
        <Grid>
          {RADII.map((token) => (
            <div key={token} style={{ textAlign: "center" }}>
              <div
                style={{
                  height: 96,
                  background: "var(--brand-secondary)",
                  borderRadius: `var(${token})`,
                  marginBottom: "var(--space-2)",
                }}
              />
              <code style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>
                {token}
              </code>
            </div>
          ))}
        </Grid>
      </Section>
    </Page>
  ),
};

export const Shadows: Story = {
  render: () => (
    <Page>
      <Section title="Тени / Shadows" description="Шкала возвышения. Цвет тени зависит от темы.">
        <Grid>
          {SHADOWS.map((token) => (
            <div key={token} style={{ textAlign: "center" }}>
              <div
                style={{
                  height: 96,
                  background: "var(--surface-elevated)",
                  borderRadius: "var(--radius-md)",
                  boxShadow: `var(${token})`,
                  marginBottom: "var(--space-4)",
                }}
              />
              <code style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>
                {token}
              </code>
            </div>
          ))}
        </Grid>
      </Section>
    </Page>
  ),
};

export const Motion: Story = {
  render: () => (
    <Page>
      <Section
        title="Движение / Motion"
        description="Длительности и кривые ускорения. Наведите на плитку, чтобы увидеть переход."
      >
        <Grid>
          {DURATIONS.map((token) => (
            <button
              type="button"
              key={token}
              style={{
                padding: "var(--space-4)",
                borderRadius: "var(--radius-md)",
                background: "var(--surface-secondary)",
                border: "1px solid var(--border-default)",
                transitionProperty: "transform, background-color",
                transitionDuration: `var(${token})`,
                transitionTimingFunction: "var(--ease-standard)",
                cursor: "pointer",
                textAlign: "left",
                font: "inherit",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = "scale(1.05)";
                e.currentTarget.style.backgroundColor = "var(--brand-accent)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = "scale(1)";
                e.currentTarget.style.backgroundColor = "var(--surface-secondary)";
              }}
            >
              <code style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>
                {token}
              </code>
            </button>
          ))}
        </Grid>
      </Section>
    </Page>
  ),
};

export const Themes: Story = {
  render: () => (
    <Page>
      <Section
        title="Темы / Themes"
        description="Единственное различие между VT Light и VT Dark — значения токенов. Переключите тему в панели инструментов Storybook: эта страница отреагирует целиком."
      >
        <div style={{ display: "flex", gap: "var(--space-4)", flexWrap: "wrap" }}>
          {["--brand-primary", "--brand-secondary", "--brand-accent"].map((token) => (
            <Swatch key={token} token={token} />
          ))}
        </div>
      </Section>
    </Page>
  ),
};
