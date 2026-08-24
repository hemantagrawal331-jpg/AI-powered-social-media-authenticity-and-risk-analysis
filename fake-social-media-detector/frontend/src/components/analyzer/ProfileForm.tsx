import { useMemo } from "react";
import type { Platform, ProfileInput, SampleSummary } from "../../types/analysis";

const PLATFORMS: { id: Platform; label: string }[] = [
  { id: "instagram", label: "Instagram" },
  { id: "twitter", label: "X / Twitter" },
  { id: "facebook", label: "Facebook" },
  { id: "tiktok", label: "TikTok" },
  { id: "linkedin", label: "LinkedIn" },
];

export function ProfileForm({
  value,
  onChange,
  samples,
  onPickSample,
  onSubmit,
  onJson,
  onImage,
  busy,
}: {
  value: ProfileInput;
  onChange: (next: ProfileInput) => void;
  samples: SampleSummary[];
  onPickSample: (id: string) => void;
  onSubmit: () => void;
  onJson: (file: File) => void;
  onImage: (file: File | null) => void;
  busy: boolean;
}) {
  const captionText = useMemo(() => value.captions.join("\n"), [value.captions]);
  const hashtagText = useMemo(() => value.hashtags.join(", "), [value.hashtags]);

  const set = <K extends keyof ProfileInput>(key: K, next: ProfileInput[K]) =>
    onChange({ ...value, [key]: next });

  return (
    <form
      className="space-y-6"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <div className="flex flex-wrap gap-2">
        {samples.map((sample) => (
          <button
            key={sample.id}
            type="button"
            onClick={() => onPickSample(sample.id)}
            className="rounded-full border border-white/10 px-3 py-1.5 text-xs text-slate-200 hover:border-accent/40 hover:text-accent"
          >
            {sample.label}
          </button>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Field label="Username">
          <input required value={value.username} onChange={(e) => set("username", e.target.value)} placeholder="@example_user" className="input" />
        </Field>
        <Field label="Platform">
          <select value={value.platform} onChange={(e) => set("platform", e.target.value as Platform)} className="input">
            {PLATFORMS.map((item) => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Display name">
          <input value={value.display_name} onChange={(e) => set("display_name", e.target.value)} className="input" />
        </Field>
        <Field label="Profile URL">
          <input value={value.profile_url} onChange={(e) => set("profile_url", e.target.value)} placeholder="https://instagram.com/example_user" className="input" />
        </Field>
        <NumberField label="Followers" value={value.followers} onChange={(n) => set("followers", n)} />
        <NumberField label="Following" value={value.following} onChange={(n) => set("following", n)} />
        <NumberField label="Posts" value={value.posts} onChange={(n) => set("posts", n)} />
        <NumberField label="Account age (days)" value={value.account_age_days} onChange={(n) => set("account_age_days", n)} />
        <NumberField label="Average likes" value={value.average_likes} onChange={(n) => set("average_likes", n)} />
        <NumberField label="Average comments" value={value.average_comments} onChange={(n) => set("average_comments", n)} />
        <NumberField label="Posts / week" value={value.posting_frequency_per_week} onChange={(n) => set("posting_frequency_per_week", n)} />
        <NumberField label="External links" value={value.external_links} onChange={(n) => set("external_links", n)} />
      </div>

      <Field label="Bio">
        <textarea value={value.bio} onChange={(e) => set("bio", e.target.value)} rows={3} className="input" />
      </Field>
      <Field label="Captions (one per line)">
        <textarea
          value={captionText}
          onChange={(e) => set("captions", e.target.value.split("\n").map((item) => item.trim()).filter(Boolean))}
          rows={3}
          className="input"
        />
      </Field>
      <Field label="Hashtags (comma separated)">
        <input
          value={hashtagText}
          onChange={(e) => set("hashtags", e.target.value.split(",").map((item) => item.trim()).filter(Boolean))}
          className="input"
        />
      </Field>

      <div className="flex flex-wrap gap-4 text-sm">
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={value.verified} onChange={(e) => set("verified", e.target.checked)} />
          Verified
        </label>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={value.has_profile_picture} onChange={(e) => set("has_profile_picture", e.target.checked)} />
          Has profile picture
        </label>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Field label="Upload JSON profile">
          <input
            type="file"
            accept="application/json"
            className="text-sm"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) onJson(file);
            }}
          />
        </Field>
        <Field label="Optional profile picture">
          <input
            type="file"
            accept="image/*"
            className="text-sm"
            onChange={(e) => onImage(e.target.files?.[0] || null)}
          />
        </Field>
      </div>

      <button
        type="submit"
        disabled={busy || !value.username.trim()}
        className="w-full rounded-2xl bg-accent px-4 py-3 font-display text-sm font-semibold text-ink-950 disabled:opacity-50"
      >
        Analyze Account
      </button>
    </form>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block space-y-1.5 text-sm">
      <span className="text-slate-400">{label}</span>
      {children}
    </label>
  );
}

function NumberField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <Field label={label}>
      <input
        type="number"
        min={0}
        value={Number.isFinite(value) ? value : 0}
        onChange={(e) => onChange(Number(e.target.value) || 0)}
        className="input"
      />
    </Field>
  );
}
