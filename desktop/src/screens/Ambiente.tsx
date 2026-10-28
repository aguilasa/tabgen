import { useEffect, useState } from "react";
import type { DoctorState } from "../App";
import type { Device, Prefs, Transcriber } from "../lib/prefs";

interface Props {
  doctor: DoctorState;
  prefs: Prefs;
  defaultPython: string;
  onPrefsChange: (prefs: Prefs) => void;
  onRecheck: () => void;
}

const DEVICES: Device[] = ["auto", "cuda", "cpu"];
const TRANSCRIBERS: Transcriber[] = ["riley", "basic-pitch"];

function Segmented<T extends string>(props: {
  options: T[];
  value: T;
  onChange: (value: T) => void;
}) {
  return (
    <div className="seg">
      {props.options.map((option) => (
        <button
          key={option}
          type="button"
          className={option === props.value ? "on" : ""}
          onClick={() => props.onChange(option)}
        >
          {option}
        </button>
      ))}
    </div>
  );
}

function errorHint(kind: string): string {
  if (kind === "SpawnError") {
    return "Não foi possível iniciar o Python nesse caminho. Ajuste o interpretador abaixo " +
      "(vazio = .venv do repositório) e verifique de novo.";
  }
  if (kind === "WorkerCrash") {
    return "O Python iniciou, mas o worker não respondeu. O tabgen está instalado nesse " +
      "interpretador? Rode `pip install -e .` no repositório (veja o README).";
  }
  return "O worker devolveu um erro ao verificar o ambiente.";
}

export default function Ambiente(props: Props) {
  const { doctor, prefs, onPrefsChange } = props;
  const [pythonDraft, setPythonDraft] = useState(prefs.pythonPath);
  useEffect(() => setPythonDraft(prefs.pythonPath), [prefs.pythonPath]);

  const commitPython = () => {
    if (pythonDraft.trim() !== prefs.pythonPath) {
      onPrefsChange({ ...prefs, pythonPath: pythonDraft.trim() });
    }
  };

  return (
    <section>
      <h2 className="sect">Ambiente</h2>

      {doctor.state === "error" && (
        <div className="errbox" role="alert">
          <div className="cn">
            {doctor.error.kind}: {doctor.error.message}
          </div>
          <p>{errorHint(doctor.error.kind)}</p>
          {doctor.error.stderr && <pre>{doctor.error.stderr}</pre>}
        </div>
      )}

      <div className="checks">
        {doctor.state === "loading" && <div className="check">Verificando…</div>}
        {(doctor.state === "ok" || doctor.state === "bad") &&
          doctor.report.checks.map((check) => (
            <div key={check.name} className={`check ${check.ok ? "ok" : "bad"}`}>
              <span className="ic">{check.ok ? "✓" : "✗"}</span>
              <div>
                <div className="cn">{check.name}</div>
                <div className="cd">{check.detail}</div>
              </div>
            </div>
          ))}
      </div>
      <div className="actions-row">
        <button
          type="button"
          className="btn btn-ghost"
          onClick={props.onRecheck}
          disabled={doctor.state === "loading"}
        >
          Verificar de novo
        </button>
      </div>

      <div className="prefs">
        <h2 className="sect">Padrões da interface</h2>
        <div className="grid">
          <label className="field wide">
            <span>Interpretador Python</span>
            <input
              type="text"
              value={pythonDraft}
              placeholder={props.defaultPython}
              onChange={(event) => setPythonDraft(event.target.value)}
              onBlur={commitPython}
              onKeyDown={(event) => event.key === "Enter" && commitPython()}
              spellCheck={false}
            />
          </label>
          <div className="field">
            <span>Dispositivo</span>
            <Segmented
              options={DEVICES}
              value={prefs.device}
              onChange={(device) => onPrefsChange({ ...prefs, device })}
            />
          </div>
          <div className="field">
            <span>Transcriber</span>
            <Segmented
              options={TRANSCRIBERS}
              value={prefs.transcriber}
              onChange={(transcriber) => onPrefsChange({ ...prefs, transcriber })}
            />
          </div>
          <label className="field">
            <span>Pasta de saída</span>
            <input
              type="text"
              value={prefs.outputDir}
              placeholder="ao lado do áudio"
              onChange={(event) => onPrefsChange({ ...prefs, outputDir: event.target.value })}
              spellCheck={false}
            />
          </label>
        </div>
        <p className="legend">
          Primeira execução baixa os pesos: Demucs ~1 GB + riley ~99 MB. Em CPU a separação
          fica 10–20× mais lenta.
        </p>
      </div>
    </section>
  );
}
