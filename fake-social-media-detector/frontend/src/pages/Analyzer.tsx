import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AnalysisLoader } from "../components/analyzer/AnalysisLoader";
import { ProfileForm } from "../components/analyzer/ProfileForm";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { GlassCard } from "../components/common/GlassCard";
import { useSamples } from "../hooks/useSamples";
import { api, persistResult } from "../services/api";
import { emptyProfile, type ProfileInput } from "../types/analysis";

export function Analyzer() {
  const navigate = useNavigate();
  const { samples } = useSamples();
  const [profile, setProfile] = useState<ProfileInput>(emptyProfile());
  const [image, setImage] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [fetchUrl, setFetchUrl] = useState("");
  const [fetchNote, setFetchNote] = useState<string | null>(null);
  const [fetching, setFetching] = useState(false);
  const [tinyfishReady, setTinyfishReady] = useState<boolean | null>(null);

  useEffect(() => {
    api
      .health()
      .then((health) => setTinyfishReady(Boolean(health.tinyfish_configured)))
      .catch(() => setTinyfishReady(null));
  }, []);

  const loadSample = async (id: string) => {
    setError(null);
    try {
      const sample = await api.sample(id);
      setProfile(sample.profile);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load sample");
    }
  };

  const onJson = async (file: File) => {
    setBusy(true);
    setError(null);
    try {
      const result = await api.analyzeUpload(file, image);
      persistResult(result);
      navigate("/results");
    } catch (err) {
      setError(err instanceof Error ? err.message : "JSON upload failed");
    } finally {
      setBusy(false);
    }
  };

  const fetchPublic = async () => {
    const url = fetchUrl.trim();
    if (!url) {
      setError("Paste a public profile URL first.");
      return;
    }
    setFetching(true);
    setError(null);
    setFetchNote("Reading the public page. This usually takes under a minute.");
    try {
      const data = await api.fetchPublicProfile(url);
      setProfile((current) => ({
        ...current,
        ...data.profile,
        captions: data.profile.captions ?? current.captions,
        hashtags: data.profile.hashtags ?? current.hashtags,
        recent_activity: current.recent_activity,
        follower_growth_events: current.follower_growth_events,
        following_growth_events: current.following_growth_events,
        engagement_history: current.engagement_history,
      }));
      setFetchNote(data.notes);
    } catch (err) {
      setFetchNote(null);
      setError(err instanceof Error ? err.message : "Could not read that public page");
    } finally {
      setFetching(false);
    }
  };

  const submit = async () => {
    if (!profile.username.trim()) {
      setError("Enter a username or load a sample profile.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      let payload = { ...profile };
      if (image) {
        payload = { ...payload, image_base64: await fileToBase64(image), image_filename: image.name, has_profile_picture: true };
      }
      const result = await api.analyze(payload);
      persistResult(result);
      navigate("/results");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setBusy(false);
    }
  };

  if (busy) return <AnalysisLoader />;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="font-display text-3xl">Analyzer</h1>
        <p className="mt-1 text-sm text-slate-400">
          Enter profile signals manually, load a sample, upload JSON, or fetch a public page.
          FakeGuard never asks for passwords or platform login.
        </p>
      </div>
      <ErrorBanner message={error} />
      <GlassCard>
        <p className="text-sm text-slate-300">
          Paste a public profile link. TinyFish reads the page anyone can see and fills the form. It does not log in.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <input
            value={fetchUrl}
            onChange={(event) => setFetchUrl(event.target.value)}
            placeholder="https://instagram.com/example"
            className="input min-w-[16rem] flex-1"
          />
          <button
            type="button"
            disabled={fetching || busy || !fetchUrl.trim() || tinyfishReady === false}
            onClick={() => void fetchPublic()}
            className="rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-ink-950 disabled:opacity-50"
          >
            {fetching ? "Reading public page…" : "Fetch public profile"}
          </button>
        </div>
        {tinyfishReady === false && (
          <p className="mt-3 text-sm text-slate-400">
            Public page fetch is off on this server. Add TINYFISH_API_KEY in the host environment, or type the profile below.
          </p>
        )}
        {fetchNote && <p className="mt-3 text-sm text-slate-400">{fetchNote}</p>}
      </GlassCard>
      <GlassCard>
        <ProfileForm
          value={profile}
          onChange={setProfile}
          samples={samples}
          onPickSample={(id) => void loadSample(id)}
          onSubmit={() => void submit()}
          onJson={(file) => void onJson(file)}
          onImage={setImage}
          busy={busy}
        />
      </GlassCard>
    </div>
  );
}

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(new Error("Image could not be read"));
    reader.readAsDataURL(file);
  });
}
