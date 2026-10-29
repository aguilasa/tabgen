// "Gerar tab ▶" drawer: the generation options of one song. Every list of
// values (tunings, guitar types, transcribers, formats, capo range) comes
// from the worker's `presets` command; custom tunings are checked by the
// worker's `tuning` command (the core's resolve_tuning) before any job.
import { save } from "@tauri-apps/plugin-dialog";
import { useEffect, useMemo, useRef, useState } from "react";
import type { Device } from "../lib/prefs";
import { formatDuration } from "../lib/recents";
import {
  coldEstimateSeconds,
  CUSTOM_TUNING,
  formatOfPath,
  README_COLD_EXPORT,
  withFormatSuffix,
  type GenerationPresets,
  type GenOptions,
  type ResolvedTuning,
  type SongMemory,
} from "../lib/run";
import { runWorker, WorkerError } from "../lib/worker";

const INSTRUMENT_LABEL: Record<string, string> = { guitar: "Guitarra", bass: "Baixo" };
const GUITAR_TYPE_LABEL: Record<string, string> = {
  electric: "elétrica",
  nylon: "nylon",
  steel: "aço",
};
const FORMAT_LABEL: Record<string, string> = { gp5: "gp5", musicxml: "MusicXML", ascii: "ASCII" };
const DEVICES: Device[] = ["auto", "cuda", "cpu"];

type Check =
  | { state: "checking" }
  | { state: "ok"; tuning: ResolvedTuning }
  | { state: "error"; message: string };

/** Worker check of each instrument's custom tuning text, debounced. */
function useCustomChecks(
  python: string,
  options: GenOptions,
): Record<string, Check | undefined> {
  const [checks, setChecks] = useState<Record<string, { spec: string; check: Check }>>({});
  const wanted = useMemo(
    () =>
      options.instruments
        .filter((name) => options.tuning[name] === CUSTOM_TUNING)
        .map((name) => [name, options.customTuning[name] ?? ""] as const),
    [options.instruments, options.tuning, options.customTuning],
  );
  const latest = useRef(wanted);
  latest.current = wanted;

  useEffect(() => {
    if (!python) return;
    const timers = wanted
      .filter(([name, spec]) => checks[name]?.spec !== spec)
      .map(([name, spec]) =>
        window.setTimeout(() => {
          const still = () => latest.current.some(([n, s]) => n === name && s === spec);
          setChecks((c) => ({ ...c, [name]: { spec, check: { state: "checking" } } }));
          runWorker<ResolvedTuning>(python, "tuning", { instrument: name, spec }).then(
            (tuning) => {
              if (still()) setChecks((c) => ({ ...c, [name]: { spec, check: { state: "ok", tuning } } }));
            },
            (err: unknown) => {
              const message =
                err instanceof WorkerError ? `${err.kind}: ${err.message}` : String(err);
              if (still())
                setChecks((c) => ({ ...c, [name]: { spec, check: { state: "error", message } } }));
            },
          );
        }, 350),
      );
    return () => timers.forEach((t) => window.clearTimeout(t));
    // `checks` is left out on purpose: it is read only to skip specs
    // already checked, and each answer must not restart the timers.
  }, [python, wanted]);

  const result: Record<string, Check | undefined> = {};
  for (const [name, spec] of wanted) {
    const entry = checks[name];
    result[name] = entry?.spec === spec ? entry.check : { state: "checking" };
  }
  return result;
}

interface Props {
  songName: string;
  durationS: number;
  python: string;
  presets: GenerationPresets;
  initial: GenOptions;
  /** Remembered run of this song (options + duration), null = never generated. */
  memory: SongMemory | null;
  /** Why the job cannot start now, or null. */
  blocked: string | null;
  onGenerate: (options: GenOptions) => void;
  onClose: () => void;
}

export default function OpcoesDrawer({
  songName,
  durationS,
  python,
  presets,
  initial,
  memory,
  blocked,
  onGenerate,
  onClose,
}: Props) {
  const [options, setOptions] = useState<GenOptions>(initial);
  const checks = useCustomChecks(python, options);
  const set = (change: Partial<GenOptions>) => setOptions((o) => ({ ...o, ...change }));

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const toggleInstrument = (name: string) => {
    const on = options.instruments.includes(name);
    const next = presets.instruments.filter((i) =>
      i === name ? !on : options.instruments.includes(i),
    );
    set({ instruments: next });
  };

  const suffixFormat = formatOfPath(presets, options.output);
  const setOutput = (output: string) => {
    const format = formatOfPath(presets, output);
    set(format ? { output, format } : { output });
  };
  const chooseOutput = async () => {
    const chosen = await save({
      defaultPath: options.output,
      filters: presets.export_formats.map((f) => ({
        name: FORMAT_LABEL[f.format] ?? f.format,
        extensions: f.suffixes.map((s) => s.slice(1)),
      })),
    }).catch(() => null);
    if (chosen) setOutput(chosen);
  };

  const [capoMin, capoMax] = presets.capo_range;
  const capoFrets = Array.from({ length: capoMax - capoMin + 1 }, (_, i) => capoMin + i);
  const guitar = options.instruments.includes("guitar");

  const problems: string[] = [];
  if (options.instruments.length === 0) problems.push("Escolha ao menos um instrumento.");
  for (const name of options.instruments) {
    const check = checks[name];
    if (check?.state === "error") problems.push(`Afinação inválida (${(INSTRUMENT_LABEL[name] ?? name).toLowerCase()}).`);
    else if (check?.state === "checking") problems.push("Validando afinação…");
  }
  if (!options.output.trim()) problems.push("Informe o arquivo de saída.");
  const reason = blocked ?? problems[0] ?? null;

  const cold = coldEstimateSeconds(durationS);

  return (
    <>
      <div className="scrim" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-label="Opções de geração" data-testid="drawer">
        <div className="drawer-head">
          <h2>Gerar tablatura</h2>
          <button type="button" className="back" onClick={onClose} title="Fechar (Esc)">
            ✕
          </button>
        </div>
        <p className="muted drawer-song">{songName}</p>

        <div className="field">
          <span>Instrumentos</span>
          {presets.instruments.map((name) => (
            <label className="checkline" key={name}>
              <input
                type="checkbox"
                checked={options.instruments.includes(name)}
                onChange={() => toggleInstrument(name)}
                data-testid={`inst-${name}`}
              />
              {INSTRUMENT_LABEL[name] ?? name}
            </label>
          ))}
        </div>

        {presets.instruments.map((name) => {
          if (!options.instruments.includes(name)) return null;
          const list = presets.tunings[name] ?? [];
          const choice = options.tuning[name] ?? presets.default_tunings[name];
          const preset = list.find((p) => p.name === choice);
          const check = checks[name];
          return (
            <div className="field" key={`tuning-${name}`}>
              <span>Afinação · {INSTRUMENT_LABEL[name] ?? name}</span>
              <select
                value={choice}
                data-testid={`tuning-${name}`}
                onChange={(e) => {
                  const value = e.target.value;
                  const change: Partial<GenOptions> = {
                    tuning: { ...options.tuning, [name]: value },
                  };
                  // start a custom tuning from the preset it replaces
                  if (value === CUSTOM_TUNING && !options.customTuning[name] && preset) {
                    change.customTuning = {
                      ...options.customTuning,
                      [name]: preset.notes.join(","),
                    };
                  }
                  set(change);
                }}
              >
                {list.map((p) => (
                  <option key={p.name} value={p.name}>
                    {p.name} ({p.notes.join(" ")})
                  </option>
                ))}
                <option value={CUSTOM_TUNING}>custom…</option>
              </select>
              {choice === CUSTOM_TUNING ? (
                <>
                  <input
                    type="text"
                    className={check?.state === "error" ? "invalid" : ""}
                    data-testid={`custom-${name}`}
                    placeholder={(list[0]?.notes ?? []).join(",")}
                    value={options.customTuning[name] ?? ""}
                    onChange={(e) =>
                      set({ customTuning: { ...options.customTuning, [name]: e.target.value } })
                    }
                  />
                  {check?.state === "error" && (
                    <span className="ferr" data-testid={`custom-${name}-error`}>
                      {check.message}
                    </span>
                  )}
                  {check?.state === "ok" && (
                    <span className="hint" data-testid={`custom-${name}-ok`}>
                      {check.tuning.notes.join(" ")} · MIDI {check.tuning.midi.join(", ")}
                      {check.tuning.name && ` · = preset ${check.tuning.name}`}
                    </span>
                  )}
                  {check?.state === "checking" && <span className="hint">validando…</span>}
                  <span className="hint">
                    Notas ou números MIDI separados por vírgula, da corda mais grave para a mais
                    aguda.
                  </span>
                </>
              ) : (
                preset && <span className="hint">MIDI {preset.midi.join(", ")}</span>
              )}
            </div>
          );
        })}

        {guitar && (
          <div className="drawer-row">
            <div className="field">
              <span>Capo</span>
              <select
                value={options.capo}
                data-testid="capo"
                onChange={(e) => set({ capo: Number(e.target.value) })}
              >
                {capoFrets.map((fret) => (
                  <option key={fret} value={fret}>
                    {fret === 0 ? "sem capo" : `casa ${fret}`}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <span>Tipo de guitarra</span>
              <div className="seg">
                {presets.guitar_types.map((type) => (
                  <button
                    type="button"
                    key={type}
                    className={options.guitarType === type ? "on" : ""}
                    data-testid={`gtype-${type}`}
                    onClick={() => set({ guitarType: type })}
                  >
                    {GUITAR_TYPE_LABEL[type] ?? type}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        <div className="field">
          <span>Transcriber</span>
          <div className="seg">
            {presets.transcribers.map((name) => (
              <button
                type="button"
                key={name}
                className={options.transcriber === name ? "on" : ""}
                data-testid={`transcriber-${name}`}
                onClick={() => set({ transcriber: name })}
              >
                {name}
              </button>
            ))}
          </div>
          <span className="hint">riley: melhor na guitarra; baixo usa sempre basic-pitch</span>
        </div>

        <div className="drawer-row">
          <div className="field">
            <span>Device</span>
            <div className="seg">
              {DEVICES.map((device) => (
                <button
                  type="button"
                  key={device}
                  className={options.device === device ? "on" : ""}
                  onClick={() => set({ device })}
                >
                  {device}
                </button>
              ))}
            </div>
          </div>
          <div className="field">
            <span>Técnicas</span>
            <label className="checkline">
              <input
                type="checkbox"
                checked={options.techniques}
                onChange={(e) => set({ techniques: e.target.checked })}
              />
              bends, slides, hammer-on/pull-off
            </label>
          </div>
        </div>

        <div className="field">
          <span>Saída</span>
          <div className="pathrow">
            <input
              type="text"
              data-testid="output"
              value={options.output}
              onChange={(e) => setOutput(e.target.value)}
            />
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => void chooseOutput()}>
              Escolher…
            </button>
          </div>
          <div className="seg">
            {presets.export_formats.map(({ format }) => (
              <button
                type="button"
                key={format}
                className={options.format === format ? "on" : ""}
                data-testid={`format-${format}`}
                onClick={() =>
                  set({ format, output: withFormatSuffix(presets, options.output, format) })
                }
              >
                {FORMAT_LABEL[format] ?? format}
              </button>
            ))}
          </div>
          <span className="hint">
            {suffixFormat
              ? "O formato segue o sufixo do arquivo."
              : "Sufixo não reconhecido: vale o formato escolhido acima."}
          </span>
        </div>

        <div className="estimate" data-testid="estimate">
          Estimativa: fria ≈ {formatDuration(cold)} · com cache &lt; 1 s
          {options.device === "cpu" && " · em CPU a separação fica 10–20× mais lenta"}
          <span className="hint">
            Escala do README (export a frio de {formatDuration(README_COLD_EXPORT.songSeconds)} em{" "}
            {README_COLD_EXPORT.runSeconds} s, RTX 3060 Laptop). Trocar afinação, capo, tipo,
            técnicas ou transcriber refaz a tablatura; o transcriber refaz também a transcrição.
          </span>
          {memory?.lastRunMs != null && (
            <span className="hint" data-testid="last-run">
              Última execução desta música:{" "}
              {(memory.lastRunMs / 1000).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} s
              {memory.lastRunCached ? " (cache)" : ""}
            </span>
          )}
        </div>

        <div className="actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancelar
          </button>
          <button
            type="button"
            className="btn btn-primary"
            data-testid="drawer-generate"
            disabled={reason !== null}
            title={reason ?? "Gerar com estas opções"}
            onClick={() => onGenerate(options)}
          >
            Gerar ▶
          </button>
        </div>
        {!blocked && problems[0] && <p className="hint drawer-reason">{problems[0]}</p>}
      </aside>
    </>
  );
}
