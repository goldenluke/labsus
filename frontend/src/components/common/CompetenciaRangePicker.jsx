import React, { useMemo } from 'react';
import { FiAlertTriangle } from 'react-icons/fi';

// Intervalo livre de competências (ano/mês inicial -> final), substituindo
// checkboxes fixas -- há ~101 meses reais de parquet SIH-SP em cache local
// (2018-01 a 2026-05), bem mais que os poucos meses antes curados à mão.
// Não valida se um estabelecimento tem dado real num mês específico (só
// descobre ao rodar, como o resto da plataforma) -- só gera a lista do
// intervalo em JS.
const SECONDS_PER_COMPETENCIA = 50; // medido nas rodadas reais desta sessão

function monthValue(ano, mes) {
    return `${ano}-${String(mes).padStart(2, '0')}`;
}

function parseMonthValue(value) {
    const [ano, mes] = value.split('-').map(Number);
    return { ano, mes };
}

function buildRange(start, end) {
    if (!start || !end) return [];
    const startDate = start.ano * 12 + (start.mes - 1);
    const endDate = end.ano * 12 + (end.mes - 1);
    if (endDate < startDate) return [];
    const competencias = [];
    for (let d = startDate; d <= endDate; d++) {
        competencias.push({ ano: Math.floor(d / 12), mes: (d % 12) + 1 });
    }
    return competencias;
}

export default function CompetenciaRangePicker({ start, end, onChange, nFacilities = 1 }) {
    const competencias = useMemo(() => buildRange(start, end), [start, end]);

    const nSpecs = competencias.length * nFacilities;
    const estimatedSeconds = nSpecs * SECONDS_PER_COMPETENCIA;
    const estimatedMinutes = Math.ceil(estimatedSeconds / 60);

    const setStart = (value) => onChange(parseMonthValue(value), end);
    const setEnd = (value) => onChange(start, parseMonthValue(value));

    return (
        <div className="space-y-2">
            <div className="grid grid-cols-2 gap-3">
                <div>
                    <label className="text-xs font-bold text-gray-500 uppercase tracking-wide block mb-1">Competência inicial</label>
                    <input
                        type="month"
                        value={start ? monthValue(start.ano, start.mes) : ''}
                        onChange={e => setStart(e.target.value)}
                        className="w-full p-2 border border-gray-300 rounded-lg text-sm"
                    />
                </div>
                <div>
                    <label className="text-xs font-bold text-gray-500 uppercase tracking-wide block mb-1">Competência final</label>
                    <input
                        type="month"
                        value={end ? monthValue(end.ano, end.mes) : ''}
                        onChange={e => setEnd(e.target.value)}
                        className="w-full p-2 border border-gray-300 rounded-lg text-sm"
                    />
                </div>
            </div>

            {competencias.length > 0 && (
                <p className="text-xs text-gray-500">
                    {competencias.length} competência(s) × {nFacilities} estabelecimento(s) = {nSpecs} consulta(s) à BPHO.
                </p>
            )}

            {estimatedMinutes >= 5 && (
                <div className="flex items-start gap-2 p-2.5 bg-amber-50 border border-amber-200 rounded-lg">
                    <FiAlertTriangle className="text-amber-500 shrink-0 mt-0.5" size={14} />
                    <p className="text-xs text-amber-700">
                        Cada consulta (estabelecimento × competência) leva ~{SECONDS_PER_COMPETENCIA}s -- essa
                        seleção deve levar cerca de <strong>{estimatedMinutes} minuto(s)</strong> para processar.
                        Reduza o intervalo ou o número de estabelecimentos para uma resposta mais rápida.
                    </p>
                </div>
            )}
        </div>
    );
}
