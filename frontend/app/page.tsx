"use client";
import { useState, useRef, useEffect } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const CATEGORIES = [
  { id: "음식점", label: "음식점", color: "#DC3232", icon: "🍽" },
  { id: "헬스", label: "헬스", color: "#1E1E1E", icon: "💪" },
  { id: "뷰티", label: "뷰티", color: "#C8AA8C", icon: "✨" },
  { id: "학원", label: "학원", color: "#329650", icon: "📚" },
  { id: "병원", label: "병원", color: "#8C6440", icon: "🏥" },
  { id: "안경", label: "안경", color: "#E68220", icon: "👓" },
  { id: "부동산", label: "부동산", color: "#2C3E6B", icon: "🏠" },
  { id: "골프", label: "골프", color: "#1A5C2A", icon: "⛳" },
  { id: "핸드폰", label: "핸드폰", color: "#0066CC", icon: "📱" },
  { id: "동물병원", label: "동물병원", color: "#4AADE8", icon: "🐾" },
  { id: "미용실", label: "미용실", color: "#D4618C", icon: "💇" },
  { id: "기타", label: "기타", color: "#4A4A4A", icon: "🏢" },
];

const BGM_GENRES = ["신남", "잔잔", "밝음", "강렬한", "클래식", "팝", "펑키"];

const SCENE_TYPES = [
  { id: "", label: "자동" },
  { id: "intro", label: "인트로" },
  { id: "feature_list", label: "특징 리스트" },
  { id: "promotion", label: "프로모션" },
  { id: "gallery", label: "갤러리" },
  { id: "cta", label: "CTA" },
  { id: "info_card", label: "정보 카드" },
  { id: "highlight", label: "하이라이트" },
  { id: "review", label: "후기" },
];

const FRAME_SIZES = [
  { id: "1080x1650", label: "1080 × 1650", desc: "숏폼 표준" },
  { id: "1080x1920", label: "1080 × 1920", desc: "9:16 풀" },
  { id: "1080x2560", label: "1080 × 2560", desc: "롱폼" },
];

const TEXT_POSITIONS = [
  { id: "", label: "자동" },
  { id: "top_left", label: "좌상" },
  { id: "top_center", label: "상단" },
  { id: "top_right", label: "우상" },
  { id: "mid_left", label: "좌중" },
  { id: "mid_center", label: "중앙" },
  { id: "mid_right", label: "우중" },
  { id: "bottom_wide", label: "하단" },
];

const MIN_SCENES = 4;
const MAX_SCENES = 10;

interface SceneData {
  headline: string;
  subtext: string;
  media_index: number;
  media_type: string;
  scene_type: string;
  text_position: string;
  font_color: string;
  emphasis_color: string;
  emphasis_words: string[];
  layout_variant: number;
  photo_mode: string;
  photo_overlay: string;
  text_effect: string;
  font_name: string;
  font_size_scale: number;
}

interface OptionItem {
  id: string;
  label: string;
}

type InputMode = "url" | "manual";
type PhotoMode = "auto" | "upload";

function createEmptyScene(index: number): SceneData {
  return {
    headline: "",
    subtext: "",
    media_index: index,
    media_type: "photo",
    scene_type: "",
    text_position: "",
    font_color: "",
    emphasis_color: "",
    emphasis_words: [],
    layout_variant: 0,
    photo_mode: "",
    photo_overlay: "",
    text_effect: "",
    font_name: "",
    font_size_scale: 1.0,
  };
}

function getSceneTimeLabel(index: number, total: number): string {
  const duration = 15 / total;
  const start = (index * duration).toFixed(1);
  const end = ((index + 1) * duration).toFixed(1);
  return `${start}-${end}초`;
}

export default function Home() {
  const [step, setStep] = useState(1);
  const [inputMode, setInputMode] = useState<InputMode>("url");
  const [photoMode, setPhotoMode] = useState<PhotoMode>("auto");

  // Place URL
  const [placeUrl, setPlaceUrl] = useState("");
  const [placeLoading, setPlaceLoading] = useState(false);
  const [placeError, setPlaceError] = useState("");
  const [autoPhotos, setAutoPhotos] = useState<string[]>([]);

  // Business info
  const [category, setCategory] = useState("");
  const [businessName, setBusinessName] = useState("");
  const [tagline, setTagline] = useState("");
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");
  const [website, setWebsite] = useState("");
  const [services, setServices] = useState<string[]>([]);
  const [serviceInput, setServiceInput] = useState("");
  const [primaryColor, setPrimaryColor] = useState("");

  // Media
  const [files, setFiles] = useState<File[]>([]);
  const [logo, setLogo] = useState<File | null>(null);

  // Scenes (동적 4~10개)
  const [scenes, setScenes] = useState<SceneData[]>([
    createEmptyScene(0),
    createEmptyScene(1),
    createEmptyScene(2),
    createEmptyScene(3),
  ]);

  // Frame size
  const [frameSize, setFrameSize] = useState("1080x1650");

  // BGM
  const [bgmMode, setBgmMode] = useState("auto");
  const [bgmGenre, setBgmGenre] = useState("");

  // Generation
  const [status, setStatus] = useState("");
  const [progress, setProgress] = useState(0);
  const [resultFile, setResultFile] = useState("");
  const [generating, setGenerating] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState("");

  // Upload state
  const [uploadDir, setUploadDir] = useState("");

  // Options (API에서 로드)
  const [fontOptions, setFontOptions] = useState<string[]>([]);
  const [effectOptions, setEffectOptions] = useState<OptionItem[]>([]);
  const [overlayOptions, setOverlayOptions] = useState<OptionItem[]>([]);
  const [photoModeOptions, setPhotoModeOptions] = useState<OptionItem[]>([]);

  // 고급 설정 토글
  const [advancedOpen, setAdvancedOpen] = useState<Record<number, boolean>>({});

  // Edit mode (생성 후)
  const [editMode, setEditMode] = useState(false);
  const [projectId, setProjectId] = useState("");
  const [previewUrls, setPreviewUrls] = useState<string[]>([]);
  const [editingScene, setEditingScene] = useState<number | null>(null);
  const [regenerating, setRegenerating] = useState(false);

  // Poll timer
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  // 옵션 데이터 로드
  useEffect(() => {
    const loadOptions = async () => {
      try {
        const [fonts, effects, overlays, modes] = await Promise.all([
          fetch(`${API}/api/options/fonts`).then(r => r.json()),
          fetch(`${API}/api/options/effects`).then(r => r.json()),
          fetch(`${API}/api/options/overlays`).then(r => r.json()),
          fetch(`${API}/api/options/photo-modes`).then(r => r.json()),
        ]);
        if (fonts.fonts) setFontOptions(fonts.fonts);
        if (effects.effects) setEffectOptions(effects.effects);
        if (overlays.overlays) setOverlayOptions(overlays.overlays);
        if (modes.photo_modes) setPhotoModeOptions(modes.photo_modes);
      } catch { /* ignore */ }
    };
    loadOptions();
  }, []);

  // --- Handlers ---

  const fetchPlaceInfo = async () => {
    if (!placeUrl.trim()) return;
    setPlaceLoading(true);
    setPlaceError("");
    try {
      const formData = new FormData();
      formData.append("url", placeUrl.trim());
      const res = await fetch(`${API}/api/place-info`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data.error) {
        setPlaceError(data.error);
        setPlaceLoading(false);
        return;
      }
      if (data.name) setBusinessName(data.name);
      if (data.category) setCategory(data.category);
      if (data.phone) setPhone(data.phone);
      if (data.address) setAddress(data.address);
      if (data.website) setWebsite(data.website);
      if (data.tagline) setTagline(data.tagline);
      if (data.services?.length) setServices(data.services);
      if (data.photo_urls?.length) {
        setAutoPhotos(data.photo_urls);
        setPhotoMode("auto");
      }
      setPlaceLoading(false);
      setStep(2);
    } catch {
      setPlaceError("서버 연결 실패. 백엔드가 실행 중인지 확인하세요.");
      setPlaceLoading(false);
    }
  };

  const downloadPlacePhotos = async (): Promise<string> => {
    if (!placeUrl.trim() || autoPhotos.length === 0) return "";
    try {
      const formData = new FormData();
      formData.append("url", placeUrl.trim());
      const res = await fetch(`${API}/api/place-photos`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) return "";
      const data = await res.json();
      if (data.upload_dir) {
        setUploadDir(data.upload_dir);
        return data.upload_dir;
      }
    } catch {
      // fallback
    }
    return "";
  };

  const addService = () => {
    if (serviceInput.trim() && services.length < 8) {
      setServices([...services, serviceInput.trim()]);
      setServiceInput("");
    }
  };

  const removeService = (idx: number) => {
    setServices(services.filter((_, i) => i !== idx));
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) setFiles(Array.from(e.target.files));
  };

  const handleLogoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) setLogo(e.target.files[0]);
  };

  const updateScene = (idx: number, field: keyof SceneData, value: string | string[] | number) => {
    const updated = [...scenes];
    updated[idx] = { ...updated[idx], [field]: value };
    setScenes(updated);
  };

  // 씬 추가/삭제
  const addScene = () => {
    if (scenes.length >= MAX_SCENES) return;
    setScenes([...scenes, createEmptyScene(scenes.length)]);
  };

  const removeScene = (idx: number) => {
    if (scenes.length <= MIN_SCENES) return;
    setScenes(scenes.filter((_, i) => i !== idx));
  };

  const moveScene = (idx: number, direction: "up" | "down") => {
    const newIdx = direction === "up" ? idx - 1 : idx + 1;
    if (newIdx < 0 || newIdx >= scenes.length) return;
    const updated = [...scenes];
    [updated[idx], updated[newIdx]] = [updated[newIdx], updated[idx]];
    setScenes(updated);
  };

  const generateAiTexts = async () => {
    setAiLoading(true);
    setAiError("");
    try {
      const res = await fetch(`${API}/api/generate-texts?num_scenes=${scenes.length}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: businessName,
          category,
          tagline,
          services,
          phone: "",
          address: "",
          website: "",
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data.scenes) {
        const newScenes: SceneData[] = data.scenes.map((s: SceneData, i: number) => ({
          headline: s.headline || "",
          subtext: s.subtext || "",
          media_index: s.media_index ?? i,
          media_type: s.media_type || "photo",
          scene_type: s.scene_type || "",
          text_position: s.text_position || "",
          font_color: s.font_color || "",
          emphasis_color: s.emphasis_color || "",
          emphasis_words: s.emphasis_words || [],
          layout_variant: scenes[i]?.layout_variant ?? 0,
          photo_mode: scenes[i]?.photo_mode ?? "",
          photo_overlay: scenes[i]?.photo_overlay ?? "",
          text_effect: scenes[i]?.text_effect ?? "",
          font_name: scenes[i]?.font_name ?? "",
          font_size_scale: scenes[i]?.font_size_scale ?? 1.0,
        }));
        setScenes(newScenes);
      } else {
        setAiError("텍스트 생성 실패. 기본 텍스트가 사용됩니다.");
      }
    } catch {
      setAiError("AI 서비스 연결 실패. 기본 텍스트가 사용됩니다.");
    }
    setAiLoading(false);
  };

  const startGeneration = async () => {
    if (!businessName.trim() || !category) return;
    setGenerating(true);
    setStatus("uploading");
    setProgress(0);
    setResultFile("");
    setEditMode(false);

    let finalUploadDir = uploadDir;
    if (photoMode === "auto" && autoPhotos.length > 0 && !uploadDir) {
      finalUploadDir = await downloadPlacePhotos();
      if (!finalUploadDir && files.length === 0) {
        setStatus("failed");
        setGenerating(false);
        return;
      }
    }

    const formData = new FormData();
    formData.append("business_name", businessName.trim());
    formData.append("category", category);
    formData.append("tagline", tagline);
    formData.append("phone", phone);
    formData.append("address", address);
    formData.append("website", website);
    formData.append("services", services.join(","));
    formData.append("primary_color", primaryColor);
    formData.append("frame_size", frameSize);
    formData.append("num_scenes", String(scenes.length));
    formData.append("bgm_genre", bgmMode === "auto" ? "" : bgmGenre);

    const hasManualText = scenes.some((s) => s.headline.trim());
    formData.append("text_mode", hasManualText ? "manual" : "ai");
    formData.append("scene_headlines", scenes.map((s) => s.headline).join("|"));
    formData.append("scene_subtexts", scenes.map((s) => s.subtext).join("|"));
    formData.append("scene_types", scenes.map((s) => s.scene_type).join("|"));
    formData.append("scene_font_colors", scenes.map((s) => s.font_color).join("|"));
    formData.append("scene_emphasis_colors", scenes.map((s) => s.emphasis_color).join("|"));
    formData.append("scene_text_positions", scenes.map((s) => s.text_position).join("|"));
    formData.append("scene_layout_variants", scenes.map((s) => String(s.layout_variant)).join("|"));
    formData.append("scene_photo_modes", scenes.map((s) => s.photo_mode).join("|"));
    formData.append("scene_photo_overlays", scenes.map((s) => s.photo_overlay).join("|"));
    formData.append("scene_text_effects", scenes.map((s) => s.text_effect).join("|"));
    formData.append("scene_font_names", scenes.map((s) => s.font_name).join("|"));
    formData.append("scene_font_size_scales", scenes.map((s) => String(s.font_size_scale)).join("|"));

    if (photoMode === "upload" && files.length > 0) {
      files.forEach((f) => formData.append("files", f));
    } else if (photoMode === "auto" && finalUploadDir) {
      formData.append("upload_dir_override", finalUploadDir);
    }

    if (logo) formData.append("logo", logo);

    try {
      const res = await fetch(`${API}/api/generate-full`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data.task_id) {
        if (data.job_id) setProjectId(data.job_id);
        pollStatus(data.task_id);
      } else {
        setStatus("failed");
        setGenerating(false);
      }
    } catch {
      setStatus("failed");
      setGenerating(false);
    }
  };

  const pollStatus = (tid: string) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API}/api/status/${tid}`);
        if (!res.ok) return;
        const data = await res.json();
        setStatus(data.status);
        setProgress(data.progress || 0);

        if (data.status === "completed") {
          setResultFile(data.filename);
          if (data.project_id) setProjectId(data.project_id);
          setGenerating(false);
          if (pollRef.current) clearInterval(pollRef.current);
          pollRef.current = null;
          // 프리뷰 로드
          loadPreviews(data.project_id || projectId);
        } else if (data.status === "failed") {
          setGenerating(false);
          if (pollRef.current) clearInterval(pollRef.current);
          pollRef.current = null;
        }
      } catch {
        // 네트워크 에러는 무시
      }
    }, 2000);
  };

  const loadPreviews = async (pid: string) => {
    if (!pid) return;
    try {
      const res = await fetch(`${API}/api/projects/${pid}`);
      if (!res.ok) return;
      const data = await res.json();
      if (data.previews) {
        setPreviewUrls(
          data.previews.map((_: string, i: number) =>
            `${API}/api/projects/${pid}/preview/${i}?t=${Date.now()}`
          )
        );
      }
    } catch {
      // ignore
    }
  };

  const enterEditMode = () => {
    if (scenes.length === 0 && projectId) {
      loadPreviews(projectId);
    }
    setEditMode(true);
    setEditingScene(null);
  };

  const updateSceneOnServer = async (idx: number) => {
    if (!projectId) return;
    const scene = scenes[idx];
    try {
      const res = await fetch(`${API}/api/projects/${projectId}/scenes/${idx}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          headline: scene.headline,
          subtext: scene.subtext,
          photo_index: scene.media_index,
          scene_type: scene.scene_type || null,
          text_position: scene.text_position || null,
          font_color: scene.font_color || null,
          emphasis_color: scene.emphasis_color || null,
          layout_variant: scene.layout_variant || 0,
          photo_overlay: scene.photo_overlay || null,
          text_effect: scene.text_effect || null,
          font_name: scene.font_name || null,
          font_size_scale: scene.font_size_scale || 1.0,
        }),
      });
      if (res.ok) {
        // 프리뷰 갱신
        setPreviewUrls((prev) => {
          const updated = [...prev];
          updated[idx] = `${API}/api/projects/${projectId}/preview/${idx}?t=${Date.now()}`;
          return updated;
        });
      }
    } catch {
      // ignore
    }
  };

  const regenerateVideo = async () => {
    if (!projectId) return;
    setRegenerating(true);
    try {
      const res = await fetch(`${API}/api/projects/${projectId}/regenerate`, {
        method: "POST",
      });
      if (!res.ok) throw new Error();
      const data = await res.json();
      if (data.task_id) {
        setGenerating(true);
        setEditMode(false);
        pollStatus(data.task_id);
      }
    } catch {
      // ignore
    }
    setRegenerating(false);
  };

  const resetAll = () => {
    setStep(1);
    setInputMode("url");
    setPhotoMode("auto");
    setPlaceUrl("");
    setPlaceError("");
    setAutoPhotos([]);
    setCategory("");
    setBusinessName("");
    setTagline("");
    setPhone("");
    setAddress("");
    setWebsite("");
    setServices([]);
    setFiles([]);
    setLogo(null);
    setScenes([
      createEmptyScene(0),
      createEmptyScene(1),
      createEmptyScene(2),
      createEmptyScene(3),
    ]);
    setFrameSize("1080x1650");
    setBgmMode("auto");
    setBgmGenre("");
    setStatus("");
    setProgress(0);
    setResultFile("");
    setGenerating(false);
    setUploadDir("");
    setAiError("");
    setEditMode(false);
    setProjectId("");
    setPreviewUrls([]);
    setEditingScene(null);
  };

  const hasPhotos =
    photoMode === "auto" ? autoPhotos.length > 0 : files.length > 0;
  const canProceedStep2 = !!businessName.trim() && !!category && hasPhotos;
  const photoCount = photoMode === "auto" ? autoPhotos.length : files.length;
  const STEP_LABELS = ["시작", "정보 & 사진", "씬 편집", "생성"];

  // --- 텍스트 위치 선택 그리드 ---
  const PositionGrid = ({ value, onChange }: { value: string; onChange: (v: string) => void }) => {
    const positions = [
      ["top_left", "top_center", "top_right"],
      ["mid_left", "mid_center", "mid_right"],
      ["bottom_wide", "bottom_wide", "bottom_wide"],
    ];
    const labels: Record<string, string> = {
      top_left: "좌상", top_center: "상단", top_right: "우상",
      mid_left: "좌중", mid_center: "중앙", mid_right: "우중",
      bottom_wide: "하단",
    };
    return (
      <div className="grid grid-cols-3 gap-1 w-full max-w-[220px]">
        {positions.flat().map((pos, i) => {
          // bottom_wide는 3칸 merge (첫번째만 렌더)
          if (pos === "bottom_wide" && i > 6) return null;
          const isBottomWide = pos === "bottom_wide" && i === 6;
          return (
            <button
              key={i}
              onClick={() => onChange(value === pos ? "" : pos)}
              className={`${isBottomWide ? "col-span-3" : ""} py-2 px-1 text-xs font-medium rounded-md transition border ${
                value === pos
                  ? "bg-blue-600 border-blue-500 text-white shadow-sm shadow-blue-500/30"
                  : "bg-gray-800/80 border-gray-600/60 text-gray-400 hover:text-white hover:bg-gray-700/80 hover:border-gray-500"
              }`}
            >
              {labels[pos]}
            </button>
          );
        })}
      </div>
    );
  };

  return (
    <main className="min-h-screen bg-[#0f0f0f] text-white">
      <div className="max-w-2xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold mb-1">포커스미디어 영상 생성기</h1>
        <p className="text-gray-500 text-sm mb-6">
          1080x1650 · 15초 · 엘리베이터/빌딩 스크린 광고
        </p>

        {/* Step indicator */}
        {!editMode && (
          <div className="flex gap-1 mb-8">
            {STEP_LABELS.map((label, i) => (
              <div
                key={i}
                className={`flex-1 text-center text-xs py-2 rounded transition-colors ${
                  step === i + 1
                    ? "bg-blue-600 text-white"
                    : step > i + 1
                    ? "bg-blue-900/60 text-blue-300"
                    : "bg-gray-800/60 text-gray-600"
                }`}
              >
                {label}
              </div>
            ))}
          </div>
        )}

        {/* ===== Step 1: 시작 ===== */}
        {step === 1 && !editMode && (
          <div>
            <h2 className="text-lg font-semibold mb-4">어떻게 시작할까요?</h2>

            <div className="flex gap-2 mb-6">
              <button
                onClick={() => setInputMode("url")}
                className={`flex-1 py-3 rounded-lg text-sm font-medium transition ${
                  inputMode === "url"
                    ? "bg-blue-600 text-white"
                    : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                }`}
              >
                플레이스 URL
              </button>
              <button
                onClick={() => setInputMode("manual")}
                className={`flex-1 py-3 rounded-lg text-sm font-medium transition ${
                  inputMode === "manual"
                    ? "bg-blue-600 text-white"
                    : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                }`}
              >
                직접 입력
              </button>
            </div>

            {inputMode === "url" && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-2">
                    네이버 플레이스 URL
                  </label>
                  <input
                    type="text"
                    value={placeUrl}
                    onChange={(e) => setPlaceUrl(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && fetchPlaceInfo()}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-sm focus:border-blue-500 focus:outline-none"
                    placeholder="https://m.place.naver.com/... 또는 naver.me/..."
                  />
                  {placeError && (
                    <p className="text-red-400 text-xs mt-2">{placeError}</p>
                  )}
                </div>
                <p className="text-xs text-gray-600">
                  URL을 넣으면 업체명, 전화번호, 주소, 사진이 자동으로
                  입력됩니다
                </p>
                <button
                  onClick={fetchPlaceInfo}
                  disabled={!placeUrl.trim() || placeLoading}
                  className="w-full py-3 bg-blue-600 rounded-lg text-sm font-semibold hover:bg-blue-500 transition disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {placeLoading ? (
                    <span className="flex items-center justify-center gap-2">
                      <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      정보 가져오는 중...
                    </span>
                  ) : (
                    "정보 가져오기"
                  )}
                </button>
              </div>
            )}

            {inputMode === "manual" && (
              <div>
                <h3 className="text-sm text-gray-400 mb-3">업종을 선택하세요</h3>
                <div className="grid grid-cols-4 gap-2">
                  {CATEGORIES.map((c) => (
                    <button
                      key={c.id}
                      onClick={() => {
                        setCategory(c.id);
                        setPhotoMode("upload");
                        setStep(2);
                      }}
                      className={`p-3 rounded-lg border text-center transition hover:scale-[1.03] ${
                        category === c.id
                          ? "border-blue-500 bg-blue-900/30"
                          : "border-gray-700/50 bg-gray-800/40 hover:border-gray-600"
                      }`}
                    >
                      <div className="text-xl mb-0.5">{c.icon}</div>
                      <div className="text-xs">{c.label}</div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ===== Step 2: 정보 & 사진 ===== */}
        {step === 2 && !editMode && (
          <div>
            <h2 className="text-lg font-semibold mb-4">
              {inputMode === "url" ? "정보 확인 & 사진" : "업체 정보 & 사진"}
            </h2>

            {inputMode === "url" && businessName && (
              <div className="bg-green-900/20 border border-green-800/40 rounded-lg px-4 py-2 mb-4 text-xs text-green-400">
                플레이스에서 정보를 가져왔습니다. 수정이 필요하면 편집하세요.
              </div>
            )}

            <div className="space-y-3">
              <div>
                <label className="block text-xs text-gray-500 mb-1">업종</label>
                <div className="flex flex-wrap gap-1.5">
                  {CATEGORIES.map((c) => (
                    <button
                      key={c.id}
                      onClick={() => setCategory(c.id)}
                      className={`px-2.5 py-1 rounded text-xs transition ${
                        category === c.id
                          ? "bg-blue-600 text-white"
                          : "bg-gray-800 text-gray-500 hover:text-gray-300"
                      }`}
                    >
                      {c.icon} {c.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs text-gray-500 mb-1">업체명 *</label>
                <input type="text" value={businessName} onChange={(e) => setBusinessName(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                  placeholder="업체명을 입력하세요" />
              </div>

              <div>
                <label className="block text-xs text-gray-500 mb-1">태그라인/슬로건</label>
                <input type="text" value={tagline} onChange={(e) => setTagline(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                  placeholder="프리미엄 휘트니스 센터" />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">전화번호</label>
                  <input type="text" value={phone} onChange={(e) => setPhone(e.target.value)}
                    className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                    placeholder="02-1234-5678" />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">웹사이트 (QR)</label>
                  <input type="text" value={website} onChange={(e) => setWebsite(e.target.value)}
                    className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                    placeholder="https://..." />
                </div>
              </div>

              <div>
                <label className="block text-xs text-gray-500 mb-1">주소</label>
                <input type="text" value={address} onChange={(e) => setAddress(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                  placeholder="서울시 강남구 역삼동 123-45" />
              </div>

              <div>
                <label className="block text-xs text-gray-500 mb-1">서비스 태그 (최대 8개)</label>
                <div className="flex gap-2 mb-2">
                  <input type="text" value={serviceInput}
                    onChange={(e) => setServiceInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addService())}
                    className="flex-1 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                    placeholder="태그 입력 후 Enter" />
                  <button onClick={addService}
                    className="px-4 py-2 bg-gray-700 rounded text-sm hover:bg-gray-600 transition">
                    추가
                  </button>
                </div>
                {services.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {services.map((s, i) => (
                      <span key={i} className="px-2.5 py-1 bg-blue-900/40 border border-blue-800/30 rounded-full text-xs flex items-center gap-1">
                        {s}
                        <button onClick={() => removeService(i)} className="text-gray-500 hover:text-red-400 ml-0.5">x</button>
                      </span>
                    ))}
                  </div>
                )}
              </div>

              <div>
                <label className="block text-xs text-gray-500 mb-1">브랜드 컬러 (선택)</label>
                <div className="flex items-center gap-2">
                  <input type="color"
                    value={primaryColor || CATEGORIES.find((c) => c.id === category)?.color || "#4A4A4A"}
                    onChange={(e) => setPrimaryColor(e.target.value)}
                    className="w-10 h-8 rounded cursor-pointer border border-gray-700" />
                  <span className="text-xs text-gray-600">미선택 시 업종 기본 컬러</span>
                  {primaryColor && (
                    <button onClick={() => setPrimaryColor("")} className="text-xs text-gray-500 hover:text-white">초기화</button>
                  )}
                </div>
              </div>
            </div>

            <div className="border-t border-gray-800 my-5" />

            <h3 className="text-sm font-medium mb-3">사진/영상 & 로고</h3>

            <div className="flex gap-2 mb-4">
              <button onClick={() => setPhotoMode("auto")} disabled={autoPhotos.length === 0}
                className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition ${
                  photoMode === "auto" ? "bg-blue-600 text-white" : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                } ${autoPhotos.length === 0 ? "opacity-40 cursor-not-allowed" : ""}`}>
                자동 수집 {autoPhotos.length > 0 && `(${autoPhotos.length}장)`}
              </button>
              <button onClick={() => setPhotoMode("upload")}
                className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition ${
                  photoMode === "upload" ? "bg-blue-600 text-white" : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                }`}>
                직접 업로드
              </button>
            </div>

            {photoMode === "auto" && autoPhotos.length > 0 && (
              <div className="mb-4">
                <p className="text-xs text-gray-500 mb-2">플레이스에서 수집된 사진 ({autoPhotos.length}장)</p>
                <div className="grid grid-cols-3 gap-2">
                  {autoPhotos.map((url, i) => (
                    <div key={i} className="aspect-square bg-gray-800 rounded-lg overflow-hidden border border-gray-700">
                      <img src={url} alt={`사진 ${i + 1}`} className="w-full h-full object-cover"
                        onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {photoMode === "auto" && autoPhotos.length === 0 && (
              <div className="bg-gray-800/50 rounded-lg p-6 text-center mb-4">
                <p className="text-gray-500 text-sm mb-2">자동 수집된 사진이 없습니다</p>
                <button onClick={() => setPhotoMode("upload")} className="text-blue-400 text-sm hover:text-blue-300">직접 업로드하기</button>
              </div>
            )}

            {photoMode === "upload" && (
              <div className="mb-4">
                <div className="border-2 border-dashed border-gray-700 rounded-lg p-6 text-center hover:border-gray-500 transition cursor-pointer">
                  <input type="file" accept="image/*,video/*" multiple onChange={handleFileChange} className="hidden" id="file-upload" />
                  <label htmlFor="file-upload" className="cursor-pointer">
                    <div className="text-gray-500 text-sm">
                      {files.length > 0 ? `${files.length}개 파일 선택됨` : "클릭하여 사진/영상 선택 (4~10개 권장)"}
                    </div>
                  </label>
                </div>
                {files.length > 0 && (
                  <div className="mt-3 grid grid-cols-4 gap-2">
                    {files.map((f, i) => (
                      <div key={i} className="bg-gray-800 rounded p-2 text-xs text-center truncate border border-gray-700">
                        {f.type.startsWith("video/") ? "🎥" : "📷"} {f.name}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            <div className="pt-2 border-t border-gray-800">
              <label className="block text-sm text-gray-400 mb-2">로고 이미지 (선택)</label>
              <div className="flex items-center gap-3">
                <input type="file" accept="image/*" onChange={handleLogoChange} className="text-sm text-gray-500" />
                {logo && <span className="text-xs text-green-400">{logo.name}</span>}
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button onClick={() => setStep(1)} className="px-4 py-2 bg-gray-800 rounded text-sm hover:bg-gray-700 transition">이전</button>
              <button onClick={() => canProceedStep2 && setStep(3)} disabled={!canProceedStep2}
                className="flex-1 py-2 bg-blue-600 rounded text-sm font-semibold disabled:opacity-40 hover:bg-blue-500 transition">다음</button>
            </div>
          </div>
        )}

        {/* ===== Step 3: 씬 편집 ===== */}
        {step === 3 && !editMode && (
          <div>
            <h2 className="text-lg font-semibold mb-4">씬 편집</h2>

            {/* 프레임 사이즈 */}
            <div className="mb-5">
              <label className="block text-xs text-gray-500 mb-2">프레임 사이즈</label>
              <div className="flex gap-2">
                {FRAME_SIZES.map((fs) => (
                  <button key={fs.id} onClick={() => setFrameSize(fs.id)}
                    className={`flex-1 py-2 rounded-lg text-center transition ${
                      frameSize === fs.id ? "bg-blue-600 text-white" : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                    }`}>
                    <div className="text-xs font-medium">{fs.label}</div>
                    <div className="text-[10px] opacity-60">{fs.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* 씬 개수 조절 + AI 텍스트 */}
            <div className="flex items-center gap-2 mb-4">
              <button onClick={generateAiTexts} disabled={aiLoading}
                className="px-4 py-2 bg-green-700/80 rounded-lg text-sm font-medium hover:bg-green-600 disabled:opacity-50 transition">
                {aiLoading ? "생성 중..." : "AI 텍스트 자동 생성"}
              </button>
              <div className="flex items-center gap-1 ml-auto">
                <span className="text-xs text-gray-500">씬 수</span>
                <button onClick={removeScene.bind(null, scenes.length - 1)} disabled={scenes.length <= MIN_SCENES}
                  className="w-7 h-7 rounded bg-gray-800 text-gray-400 text-sm hover:bg-gray-700 disabled:opacity-30 transition">-</button>
                <span className="text-sm font-medium w-6 text-center">{scenes.length}</span>
                <button onClick={addScene} disabled={scenes.length >= MAX_SCENES}
                  className="w-7 h-7 rounded bg-gray-800 text-gray-400 text-sm hover:bg-gray-700 disabled:opacity-30 transition">+</button>
              </div>
            </div>
            {aiError && <p className="text-xs text-yellow-400 mb-2">{aiError}</p>}
            {!aiError && scenes.some((s) => s.headline) && (
              <p className="text-xs text-green-400 mb-2">텍스트 준비됨</p>
            )}

            {/* 씬 카드들 */}
            <div className="space-y-3 mb-5">
              {scenes.map((scene, i) => (
                <div key={i} className="bg-gray-800/60 border border-gray-700/50 rounded-lg p-3">
                  {/* 씬 헤더 */}
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-1.5">
                      <div className="flex flex-col gap-0.5">
                        <button onClick={() => moveScene(i, "up")} disabled={i === 0}
                          className="text-[10px] text-gray-600 hover:text-white disabled:opacity-20 leading-none">▲</button>
                        <button onClick={() => moveScene(i, "down")} disabled={i === scenes.length - 1}
                          className="text-[10px] text-gray-600 hover:text-white disabled:opacity-20 leading-none">▼</button>
                      </div>
                      <span className="text-xs text-gray-400">
                        씬 {i + 1} · {getSceneTimeLabel(i, scenes.length)}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <select value={scene.scene_type} onChange={(e) => updateScene(i, "scene_type", e.target.value)}
                        className="bg-gray-900 border border-gray-700 rounded px-2 py-1 text-xs text-gray-300 focus:border-blue-500 focus:outline-none">
                        {SCENE_TYPES.map((st) => (
                          <option key={st.id} value={st.id}>{st.label}</option>
                        ))}
                      </select>
                      <select value={scene.media_index} onChange={(e) => updateScene(i, "media_index", e.target.value)}
                        className="bg-gray-900 border border-gray-700 rounded px-2 py-1 text-xs text-gray-300 focus:border-blue-500 focus:outline-none">
                        {Array.from({ length: Math.max(photoCount, 10) }, (_, j) => (
                          <option key={j} value={j}>사진 {j + 1}</option>
                        ))}
                      </select>
                      {scenes.length > MIN_SCENES && (
                        <button onClick={() => removeScene(i)} className="text-gray-600 hover:text-red-400 text-xs">삭제</button>
                      )}
                    </div>
                  </div>

                  {/* 텍스트 입력 */}
                  <input type="text" value={scene.headline} onChange={(e) => updateScene(i, "headline", e.target.value)}
                    className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-1.5 text-sm mb-1.5 focus:border-blue-500 focus:outline-none"
                    placeholder="헤드라인 (15자 이내)" />
                  <textarea value={scene.subtext} onChange={(e) => updateScene(i, "subtext", e.target.value)}
                    className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-1.5 text-sm h-12 resize-none focus:border-blue-500 focus:outline-none"
                    placeholder="서브텍스트 (줄바꿈: Enter, 40자 이내)" />

                  {/* 하단 옵션: 텍스트 위치 + 폰트 색상 */}
                  <div className="flex items-start gap-3 mt-2 pt-2 border-t border-gray-700/40">
                    <div>
                      <span className="text-xs text-gray-400 font-medium block mb-1.5">텍스트 위치</span>
                      <PositionGrid value={scene.text_position} onChange={(v) => updateScene(i, "text_position", v)} />
                    </div>
                    <div className="flex-1 space-y-1.5">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] text-gray-600">폰트 색상</span>
                        <input type="color" value={scene.font_color || "#FFFFFF"}
                          onChange={(e) => updateScene(i, "font_color", e.target.value)}
                          className="w-6 h-5 rounded cursor-pointer border border-gray-700" />
                        {scene.font_color && (
                          <button onClick={() => updateScene(i, "font_color", "")} className="text-[10px] text-gray-600 hover:text-white">초기화</button>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] text-gray-600">강조 색상</span>
                        <input type="color" value={scene.emphasis_color || primaryColor || CATEGORIES.find((c) => c.id === category)?.color || "#FF5050"}
                          onChange={(e) => updateScene(i, "emphasis_color", e.target.value)}
                          className="w-6 h-5 rounded cursor-pointer border border-gray-700" />
                        {scene.emphasis_color && (
                          <button onClick={() => updateScene(i, "emphasis_color", "")} className="text-[10px] text-gray-600 hover:text-white">초기화</button>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* 고급 설정 토글 */}
                  <button
                    onClick={() => setAdvancedOpen(prev => ({ ...prev, [i]: !prev[i] }))}
                    className="w-full mt-2 pt-2 border-t border-gray-700/40 text-[11px] text-gray-500 hover:text-gray-300 transition flex items-center justify-center gap-1"
                  >
                    고급 설정 {advancedOpen[i] ? "▲" : "▼"}
                  </button>

                  {advancedOpen[i] && (
                    <div className="mt-2 space-y-2 bg-gray-900/40 rounded-lg p-2.5">
                      <div className="grid grid-cols-2 gap-2">
                        {/* 레이아웃 변형 */}
                        <div>
                          <span className="text-[10px] text-gray-600 block mb-0.5">레이아웃 변형</span>
                          <select value={scene.layout_variant} onChange={(e) => updateScene(i, "layout_variant", Number(e.target.value))}
                            className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1 text-xs text-gray-300 focus:border-blue-500 focus:outline-none">
                            <option value={0}>기본</option>
                            <option value={1}>변형 1</option>
                            <option value={2}>변형 2</option>
                          </select>
                        </div>

                        {/* 사진 배치 */}
                        <div>
                          <span className="text-[10px] text-gray-600 block mb-0.5">사진 배치</span>
                          <select value={scene.photo_mode} onChange={(e) => updateScene(i, "photo_mode", e.target.value)}
                            className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1 text-xs text-gray-300 focus:border-blue-500 focus:outline-none">
                            <option value="">자동</option>
                            {photoModeOptions.map(o => (
                              <option key={o.id} value={o.id}>{o.label}</option>
                            ))}
                          </select>
                        </div>

                        {/* 오버레이 */}
                        <div>
                          <span className="text-[10px] text-gray-600 block mb-0.5">오버레이</span>
                          <select value={scene.photo_overlay} onChange={(e) => updateScene(i, "photo_overlay", e.target.value)}
                            className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1 text-xs text-gray-300 focus:border-blue-500 focus:outline-none">
                            <option value="">자동</option>
                            {overlayOptions.map(o => (
                              <option key={o.id} value={o.id}>{o.label}</option>
                            ))}
                          </select>
                        </div>

                        {/* 텍스트 효과 */}
                        <div>
                          <span className="text-[10px] text-gray-600 block mb-0.5">텍스트 효과</span>
                          <select value={scene.text_effect} onChange={(e) => updateScene(i, "text_effect", e.target.value)}
                            className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1 text-xs text-gray-300 focus:border-blue-500 focus:outline-none">
                            <option value="">자동</option>
                            {effectOptions.map(o => (
                              <option key={o.id} value={o.id}>{o.label}</option>
                            ))}
                          </select>
                        </div>

                        {/* 폰트 선택 */}
                        <div>
                          <span className="text-[10px] text-gray-600 block mb-0.5">폰트</span>
                          <select value={scene.font_name} onChange={(e) => updateScene(i, "font_name", e.target.value)}
                            className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1 text-xs text-gray-300 focus:border-blue-500 focus:outline-none">
                            <option value="">자동</option>
                            {fontOptions.map(f => (
                              <option key={f} value={f}>{f}</option>
                            ))}
                          </select>
                        </div>

                        {/* 폰트 크기 */}
                        <div>
                          <span className="text-[10px] text-gray-600 block mb-0.5">
                            폰트 크기 ({(scene.font_size_scale * 100).toFixed(0)}%)
                          </span>
                          <input type="range" min="50" max="200" step="10"
                            value={scene.font_size_scale * 100}
                            onChange={(e) => updateScene(i, "font_size_scale", Number(e.target.value) / 100)}
                            className="w-full h-1.5 accent-blue-500" />
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* BGM */}
            <div className="mb-6">
              <label className="block text-xs text-gray-500 mb-2">BGM</label>
              <div className="flex gap-2 mb-2">
                <button onClick={() => setBgmMode("auto")}
                  className={`px-3 py-1.5 rounded text-xs transition ${
                    bgmMode === "auto" ? "bg-blue-600 text-white" : "bg-gray-800 text-gray-500 hover:text-gray-300"
                  }`}>
                  자동 ({category})
                </button>
                <button onClick={() => setBgmMode("manual")}
                  className={`px-3 py-1.5 rounded text-xs transition ${
                    bgmMode === "manual" ? "bg-blue-600 text-white" : "bg-gray-800 text-gray-500 hover:text-gray-300"
                  }`}>
                  직접 선택
                </button>
              </div>
              {bgmMode === "manual" && (
                <div className="flex flex-wrap gap-2">
                  {BGM_GENRES.map((g) => (
                    <button key={g} onClick={() => setBgmGenre(g)}
                      className={`px-3 py-1.5 rounded text-xs transition ${
                        bgmGenre === g ? "bg-purple-600 text-white" : "bg-gray-800 text-gray-500 hover:text-gray-300"
                      }`}>
                      {g}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="flex gap-3">
              <button onClick={() => setStep(2)} className="px-4 py-2 bg-gray-800 rounded text-sm hover:bg-gray-700 transition">이전</button>
              <button onClick={() => setStep(4)}
                className="flex-1 py-2 bg-blue-600 rounded text-sm font-semibold hover:bg-blue-500 transition">다음</button>
            </div>
          </div>
        )}

        {/* ===== Step 4: 생성 ===== */}
        {step === 4 && !editMode && (
          <div>
            <h2 className="text-lg font-semibold mb-4">영상 생성</h2>

            {/* 요약 카드 */}
            <div className="bg-gray-800/50 rounded-lg p-4 mb-5 text-sm space-y-1.5 border border-gray-700/50">
              <div className="flex justify-between">
                <span className="text-gray-500">업종</span>
                <span>{CATEGORIES.find((c) => c.id === category)?.icon} {category}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">업체명</span>
                <span>{businessName}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">사이즈</span>
                <span>{FRAME_SIZES.find((f) => f.id === frameSize)?.label}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">사진</span>
                <span>{photoMode === "auto" ? `자동 수집 ${autoPhotos.length}장` : `직접 업로드 ${files.length}개`}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">씬 수</span>
                <span>{scenes.length}개 (15초)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">씬 텍스트</span>
                <span>{scenes.some((s) => s.headline.trim()) ? "직접 입력" : "AI 자동"}</span>
              </div>
            </div>

            {!generating && !resultFile && (
              <>
                <button onClick={startGeneration}
                  className="w-full py-3.5 bg-blue-600 rounded-lg font-semibold text-base hover:bg-blue-500 transition">
                  영상 만들기
                </button>
                <button onClick={() => setStep(3)}
                  className="mt-3 w-full py-2 bg-gray-800 rounded text-sm text-gray-400 hover:bg-gray-700 transition">
                  이전으로
                </button>
              </>
            )}

            {generating && (
              <div className="space-y-3">
                <div className="w-full bg-gray-800 rounded-full h-3 overflow-hidden">
                  <div className="bg-gradient-to-r from-blue-600 to-blue-400 h-3 rounded-full transition-all duration-500"
                    style={{ width: `${progress}%` }} />
                </div>
                <div className="text-center text-sm text-gray-400">
                  {status === "uploading" && "업로드 중..."}
                  {status === "processing" && `영상 생성 중... ${progress}%`}
                  {status === "pending" && "대기 중..."}
                  {!["uploading", "processing", "pending", "completed", "failed"].includes(status) && `${status}... ${progress}%`}
                </div>
              </div>
            )}

            {resultFile && (
              <div className="text-center space-y-4">
                <div className="text-green-400 font-semibold text-lg">영상 생성 완료!</div>
                <video
                  src={`${API}/api/download/${resultFile}`}
                  controls
                  className="w-full max-w-md mx-auto rounded-xl mb-2"
                />
                <div className="flex gap-3 justify-center">
                  <a href={`${API}/api/download/${resultFile}`}
                    className="inline-block px-8 py-3 bg-green-600 rounded-lg font-semibold hover:bg-green-500 transition">
                    다운로드
                  </a>
                  <button onClick={enterEditMode}
                    className="px-8 py-3 bg-purple-600 rounded-lg font-semibold hover:bg-purple-500 transition">
                    편집하기
                  </button>
                </div>
                <button onClick={resetAll} className="block mx-auto text-sm text-gray-500 hover:text-white transition">
                  새로 만들기
                </button>
              </div>
            )}

            {status === "failed" && !generating && (
              <div className="text-center mt-4">
                <p className="text-red-400 mb-3">생성 실패. 다시 시도해주세요.</p>
                <button onClick={() => { setStatus(""); setProgress(0); }}
                  className="text-sm text-gray-400 hover:text-white">다시 시도</button>
              </div>
            )}
          </div>
        )}

        {/* ===== 편집 모드 ===== */}
        {editMode && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">씬 편집</h2>
              <div className="flex gap-2">
                <button onClick={regenerateVideo} disabled={regenerating}
                  className="px-4 py-2 bg-blue-600 rounded-lg text-sm font-medium hover:bg-blue-500 disabled:opacity-50 transition">
                  {regenerating ? "재생성 중..." : "영상 재생성"}
                </button>
                <button onClick={() => setEditMode(false)}
                  className="px-4 py-2 bg-gray-800 rounded-lg text-sm hover:bg-gray-700 transition">닫기</button>
              </div>
            </div>

            {/* 프리뷰 그리드 */}
            <div className="grid grid-cols-2 gap-3 mb-4">
              {scenes.map((scene, i) => (
                <div key={i}
                  onClick={() => setEditingScene(editingScene === i ? null : i)}
                  className={`cursor-pointer rounded-lg overflow-hidden border-2 transition ${
                    editingScene === i ? "border-blue-500" : "border-gray-700/50 hover:border-gray-600"
                  }`}>
                  {previewUrls[i] ? (
                    <img src={previewUrls[i]} alt={`씬 ${i + 1}`} className="w-full aspect-[9/16] object-cover" />
                  ) : (
                    <div className="w-full aspect-[9/16] bg-gray-800 flex items-center justify-center text-gray-600 text-sm">
                      씬 {i + 1}
                    </div>
                  )}
                  <div className="p-2 bg-gray-800/80 text-xs">
                    <div className="text-gray-400">{getSceneTimeLabel(i, scenes.length)}</div>
                    <div className="truncate">{scene.headline || "(텍스트 없음)"}</div>
                  </div>
                </div>
              ))}
            </div>

            {/* 선택된 씬 편집 패널 */}
            {editingScene !== null && editingScene < scenes.length && (
              <div className="bg-gray-800/60 border border-blue-500/30 rounded-lg p-4 space-y-3">
                <h3 className="text-sm font-medium text-blue-400">
                  씬 {editingScene + 1} 편집 · {getSceneTimeLabel(editingScene, scenes.length)}
                </h3>

                <div>
                  <label className="block text-xs text-gray-500 mb-1">헤드라인</label>
                  <input type="text" value={scenes[editingScene].headline}
                    onChange={(e) => updateScene(editingScene, "headline", e.target.value)}
                    className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
                </div>

                <div>
                  <label className="block text-xs text-gray-500 mb-1">서브텍스트</label>
                  <textarea value={scenes[editingScene].subtext}
                    onChange={(e) => updateScene(editingScene, "subtext", e.target.value)}
                    className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm h-16 resize-none focus:border-blue-500 focus:outline-none" />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">씬 타입</label>
                    <select value={scenes[editingScene].scene_type}
                      onChange={(e) => updateScene(editingScene, "scene_type", e.target.value)}
                      className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm focus:border-blue-500 focus:outline-none">
                      {SCENE_TYPES.map((st) => (
                        <option key={st.id} value={st.id}>{st.label}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">사진 선택</label>
                    <select value={scenes[editingScene].media_index}
                      onChange={(e) => updateScene(editingScene, "media_index", e.target.value)}
                      className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm focus:border-blue-500 focus:outline-none">
                      {Array.from({ length: Math.max(photoCount, 10) }, (_, j) => (
                        <option key={j} value={j}>사진 {j + 1}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="flex items-start gap-4">
                  <div>
                    <span className="text-xs text-gray-500 block mb-1">텍스트 위치</span>
                    <PositionGrid value={scenes[editingScene].text_position}
                      onChange={(v) => updateScene(editingScene, "text_position", v)} />
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-500">폰트 색상</span>
                      <input type="color" value={scenes[editingScene].font_color || "#FFFFFF"}
                        onChange={(e) => updateScene(editingScene, "font_color", e.target.value)}
                        className="w-7 h-6 rounded cursor-pointer border border-gray-700" />
                      {scenes[editingScene].font_color && (
                        <button onClick={() => updateScene(editingScene, "font_color", "")}
                          className="text-[10px] text-gray-600 hover:text-white">초기화</button>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-500">강조 색상</span>
                      <input type="color" value={scenes[editingScene].emphasis_color || "#FF5050"}
                        onChange={(e) => updateScene(editingScene, "emphasis_color", e.target.value)}
                        className="w-7 h-6 rounded cursor-pointer border border-gray-700" />
                      {scenes[editingScene].emphasis_color && (
                        <button onClick={() => updateScene(editingScene, "emphasis_color", "")}
                          className="text-[10px] text-gray-600 hover:text-white">초기화</button>
                      )}
                    </div>
                  </div>
                </div>

                {/* 고급 편집 옵션 */}
                <div className="border-t border-gray-700/40 pt-3 space-y-2">
                  <span className="text-xs text-gray-500 font-medium">고급 설정</span>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <span className="text-[10px] text-gray-600 block mb-0.5">레이아웃 변형</span>
                      <select value={scenes[editingScene].layout_variant}
                        onChange={(e) => updateScene(editingScene, "layout_variant", Number(e.target.value))}
                        className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-xs focus:border-blue-500 focus:outline-none">
                        <option value={0}>기본</option>
                        <option value={1}>변형 1</option>
                        <option value={2}>변형 2</option>
                      </select>
                    </div>
                    <div>
                      <span className="text-[10px] text-gray-600 block mb-0.5">사진 배치</span>
                      <select value={scenes[editingScene].photo_mode}
                        onChange={(e) => updateScene(editingScene, "photo_mode", e.target.value)}
                        className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-xs focus:border-blue-500 focus:outline-none">
                        <option value="">자동</option>
                        {photoModeOptions.map(o => (
                          <option key={o.id} value={o.id}>{o.label}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <span className="text-[10px] text-gray-600 block mb-0.5">오버레이</span>
                      <select value={scenes[editingScene].photo_overlay}
                        onChange={(e) => updateScene(editingScene, "photo_overlay", e.target.value)}
                        className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-xs focus:border-blue-500 focus:outline-none">
                        <option value="">자동</option>
                        {overlayOptions.map(o => (
                          <option key={o.id} value={o.id}>{o.label}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <span className="text-[10px] text-gray-600 block mb-0.5">텍스트 효과</span>
                      <select value={scenes[editingScene].text_effect}
                        onChange={(e) => updateScene(editingScene, "text_effect", e.target.value)}
                        className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-xs focus:border-blue-500 focus:outline-none">
                        <option value="">자동</option>
                        {effectOptions.map(o => (
                          <option key={o.id} value={o.id}>{o.label}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <span className="text-[10px] text-gray-600 block mb-0.5">폰트</span>
                      <select value={scenes[editingScene].font_name}
                        onChange={(e) => updateScene(editingScene, "font_name", e.target.value)}
                        className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-xs focus:border-blue-500 focus:outline-none">
                        <option value="">자동</option>
                        {fontOptions.map(f => (
                          <option key={f} value={f}>{f}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <span className="text-[10px] text-gray-600 block mb-0.5">
                        폰트 크기 ({(scenes[editingScene].font_size_scale * 100).toFixed(0)}%)
                      </span>
                      <input type="range" min="50" max="200" step="10"
                        value={scenes[editingScene].font_size_scale * 100}
                        onChange={(e) => updateScene(editingScene, "font_size_scale", Number(e.target.value) / 100)}
                        className="w-full h-1.5 accent-blue-500 mt-1" />
                    </div>
                  </div>
                </div>

                <button onClick={() => updateSceneOnServer(editingScene)}
                  className="w-full py-2 bg-purple-600 rounded-lg text-sm font-medium hover:bg-purple-500 transition">
                  프리뷰 업데이트
                </button>
              </div>
            )}

            <div className="mt-4 flex gap-3">
              <a href={`${API}/api/download/${resultFile}`}
                className="flex-1 py-2 bg-green-600 rounded-lg text-sm font-semibold text-center hover:bg-green-500 transition">
                현재 영상 다운로드
              </a>
              <button onClick={resetAll}
                className="px-4 py-2 bg-gray-800 rounded-lg text-sm hover:bg-gray-700 transition">새로 만들기</button>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
