import { useState } from "react";
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
          Enter profile signals manually, load a sample, or upload JSON. FakeGuard never asks for
          passwords or platform login.
        </p>
      </div>
      <ErrorBanner message={error} />
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
