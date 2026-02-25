#!/usr/bin/env python3
"""
Panelin v4.0 - Batch Test Runner
===================================

Run the full Panelin v4.0 pipeline against the real-world batch of quotations
from the 2026-02-24 test run.

Usage:
    python3 panelin_v4/run_batch_test.py
"""

import json
import sys
import time

from panelin_v4.engine.quotation_engine import process_quotation, process_batch
from panelin_v4.engine.classifier import OperatingMode
from panelin_v4.evaluator.sai_engine import calculate_sai, calculate_batch_sai
from panelin_v4.evaluator.regression_suite import run_regression_suite
from panelin_v4.evaluator.stress_test_runner import run_stress_test


REAL_WORLD_BATCH = [
    {"text": "12 Goteros Frontales 100 mm + 8 Goteros Laterales 100 mm + flete",
     "client_name": "Ezequiel", "client_location": "Piriapolis"},
    {"text": "Actualizar cotización Montfrío - agregar 1 isopanel 100mm de pared de 2.40m + 1 panel techo de 3.60 + 1 ángulo estructural Aluminio",
     "client_name": "H Souza"},
    {"text": "Isodec 200 mm / 7 p. de 8 m de largo + accesorios estándar y anclajes a metal + entrega en Colon",
     "client_name": "Mauricio", "client_location": "Colon, Mvdeo"},
    {"text": "Isopanel 100 mm: 14p de 2.4 + 4p de 2.2 + 1p de 1.20 / Isodec 100 mm: 7p de 5mts",
     "client_name": "Gonzalo Nalerio", "client_location": "Chuy Rocha"},
    {"text": "ACTUALIZAR PRESUPUESTO / Isopanel 100 mm / 3 p. de 2,30 m + 1 Isodec 100 mm de 3,05 m / + 30 tortugas / Entrega en Agencia Turil Mvdeo",
     "client_name": "Rogelio Da Silva", "client_location": "Agencia Turil"},
    {"text": "Canalón 100 mm / 3 piezas de 3 m + 2 soportes + 2 tapas + 1 embudo + 3 siliconas + 100 remaches + flete",
     "client_name": "Mauricio Fripp", "client_location": "Zona Pinamar"},
    {"text": "Isopanel 200 mm y 100/150 / Habitacion completa 4.50 x 8.50 / altura 2,5 y 3 mts",
     "client_name": "Cristian"},
    {"text": "Isopanel 50 mm / 13 paneles de 2,60 mts",
     "client_name": "Andres"},
    {"text": "Isodec EPS 100 mm / 3p de 12 mts + 6p de 10 mts + 4p de 6 mts",
     "client_name": "Stefanie"},
    {"text": "Isopanel 100 mm / 3 p. de 2,30 m + 1 de 3,05 m / solo precio del panel de fachada",
     "client_name": "Rogelio Da Silva"},
    {"text": "Isoroof 50 mm / 22 p. de 4,60 m / 2 aguas / 1 lado con canalón, todo a metal + flete",
     "client_name": "Jorge Moreno", "client_location": "Charqueada - 33"},
    {"text": "Isodec 150 mm / 6 p. de 6,50 m / completo a H° + flete",
     "client_name": "Yoana Gonzalez", "client_location": "La Teja, Mvdeo"},
    {"text": "Isoroof 30mm / 4 de 6,60 m + 3 de 4,60 m + 1 de 5,80 m / + 90 tornillos p. aguja + 90 arandelas trapezoidal / Solo esto + Flete",
     "client_name": "Lo de Virginia", "client_location": "La Paloma, Rocha"},
    {"text": "Isodec 100 mm / techo 7 ancho x 10 largo",
     "client_name": "Nacho"},
    {"text": "Isodec 50 y 100 mm / 3x3 x puerta",
     "client_name": "Fabiana Paola", "client_location": "Pando"},
    {"text": "Isodec 150 mm / 8 p. de 6,50 m / + goteros + flete",
     "client_name": "Bernardo Peres", "client_location": "Maldonado"},
    {"text": "Hiansa 30mm / 3,25 mts de largo x dos aguas de 10 mts",
     "client_name": "Ramiro Portugau", "client_location": "La Barra"},
    {"text": "Isodec 150 mm / 9,6 mts ancho x 4,9 mts de largo / a metal / completo",
     "client_name": "Javier", "client_location": "Punta Colorada"},
    {"text": "Isodec 150 mm / 7m x 6m / completo",
     "client_name": "Belen Buceta"},
    {"text": "Hiansa 30 mm / 10 p. de 4,95 m / completo a H° + intermedio madera / completo + flete",
     "client_name": "Leonardo Castro", "client_location": "Piriapolis"},
    {"text": "3 opciones / Isodec 80 mm PIR / Isodec 100 mm EPS / Isopanel 150 mm EPS / 9 p. de 4,50 m / + flete SOLO",
     "client_name": "Valen", "client_location": "Mvdeo - Nuevo Centro"},
    {"text": "Barbacoa de 11 x 5 m / Isopanel 100 mm h 3m a 2,40 m + Isodec 11 p. de 6 m / completo + flete",
     "client_name": "Paola y Sergio", "client_location": "Maldonado"},
    {"text": "Isopanel 50 mm / 6 p 2,5 mts + Perfil U para solo frontal / sin anclajes",
     "client_name": "Alexis Fernandez"},
    {"text": "3 Goteros Frontales Simples Gris Panel + flete 25 dol",
     "client_name": "Paul", "client_location": "Vilardebó y Gral Flores - Mvdeo"},
    {"text": "Isodec 150 mm / 3 p de 4,38 m / + Canalones para los 3 m + 4 babetas + accesorios de instalación + flete a Pocitos",
     "client_name": "Analia Castro", "client_location": "Zona Pocitos"},
    {"text": "6 U de 120 mm / + envío",
     "client_name": "Gabriel Pickenhain", "client_location": "San Carlos"},
    {"text": "Isodec 150 mm - Gris - 5 paneles x 5.92 de largo / goteros + babeta superior / a Metal",
     "client_name": "Hector", "client_location": "Punta del Este"},
    {"text": "3 opciones / Isodec 150, 200 y 250 mm / 13 p. de 10 m / completo a metal + flete",
     "client_name": "Dominika", "client_location": "Paysandú"},
    {"text": "2 opciones: Isoroof 80 mm y Isodec 150 mm GRIS / 5 paneles de 11 mts + 6 paneles de 6 metros / anclaje a Hormigón / completo con goteros perimetrales",
     "client_name": "Lalo", "client_location": "Punta del Diablo"},
    {"text": "Isodec Isopanel 200 mm / estructura de 12 x 4 x 2,4 mts de alto / completo",
     "client_name": "Mauro"},
    {"text": "Canalones de 150 mm / 14 tramos de 9 m de largo + 2 tapas + bandeja + 1 embudo",
     "client_name": "Lady Daiana"},
    {"text": "Isopanel 100 mm / 3 paredes / 45 + 15 + 45 / de 2 m de alto / completo + flete",
     "client_name": "Rodolfo", "client_location": "Santa Lucia"},
    {"text": "Isodec 100 mm: 6p de 3mts / Isopanel 100 mm: 3p de 2.54 mts",
     "client_name": "Sebastian Corujo", "client_location": "Florida, Ciudad"},
    {"text": "Isodec 100 mm / techo de 9x6",
     "client_name": "Erika Lucia"},
    {"text": "Isopanel EPS 100mm / 3 de 2.40 + 6 de 2.50 / Isodec EPS 100mm / 3 de 3.60",
     "client_name": "Mathias"},
    {"text": "Isodec EPS 100mm / 7.90m ancho x 3.90m largo / Completo con canalón y goteros laterales + Flete",
     "client_name": "Joel"},
    {"text": "Isoroof 50mm / solo goteros perimetrales / 5p de 5,8mts",
     "client_name": "Nicolas", "client_location": "La Paz"},
    {"text": "Isodec EPS 100 mm / 8 p. de 3.90 m / Completo a H° + flete",
     "client_name": "Joel José", "client_location": "Mvdeo Conciliación"},
    {"text": "Isodec EPS 100mm / 22 paneles para techo de 10cm de 7mt / Solo + Flete",
     "client_name": "Gabriel Rubi", "client_location": "Paysandú, Ciudad"},
    {"text": "Isodec EPS 150mm / 10m ancho x 5m largo / Completo goteros perimetrales + Flete",
     "client_name": "BBC Kids"},
    {"text": "Hiansa / 2 placas de 4,95 m / accesorios y anclajes separados",
     "client_name": "Mauri", "client_location": "Mvdeo"},
    {"text": "2 opciones / Isodec 150 y 200 mm / 9p de 9 mts / frontal gotero o canalón + lateral babeta + sup gotero / a Metal",
     "client_name": "Eduardo", "client_location": "Nuevo Paris"},
    {"text": "Isodec 250 mm / 32 p. de 8,30 m + 7 p. de 3,80 m / techo Mariposa / Canalón de Hormigón, fijación a Hormigón / completo + flete",
     "client_name": "Cristian Constructora B&D", "client_location": "Solymar"},
    {"text": "Isodec 100 mm / 4p de 5.6 mts / viga en pendiente mayor y loza en caída",
     "client_name": "Fernando", "client_location": "Ciudad de la Costa"},
    {"text": "Isodec 100 mm / 12 p. 4,50 m / completo / SIN FLETE",
     "client_name": "Bruno"},
    {"text": "Cubierta Isodec 200 mm / 16 p. de 8,10 m de largo / completo a metal",
     "client_name": "Josue"},
    {"text": "Isodec 100 mm / 6p x 3 mts / Completo a Metal + Flete",
     "client_name": "Edgar", "client_location": "Soriano, Mercedes"},
    {"text": "Isoroof 30 mm / 3 p de 3,5 mts / perfil de apoyo",
     "client_name": "Carlos Ortiz", "client_location": "Toledo"},
    {"text": "Isodec 100 mm / 3 p. de 6 m / completo a Hormigón / babetas superiores y laterales + goteros frontales + flete",
     "client_name": "Elido", "client_location": "Hipódromo Maldo"},
]


def main():
    print("=" * 80)
    print("PANELIN v4.0 - BATCH TEST RUN")
    print("=" * 80)
    print()

    # Run batch
    start = time.perf_counter()
    outputs = process_batch(REAL_WORLD_BATCH, force_mode=OperatingMode.PRE_COTIZACION)
    elapsed = (time.perf_counter() - start) * 1000

    print(f"Processed {len(outputs)} quotations in {elapsed:.1f}ms")
    print(f"Average: {elapsed / len(outputs):.2f}ms per quotation")
    print()

    # Summary
    statuses = {}
    levels = {}
    blocked = 0
    total_usd = 0

    for i, output in enumerate(outputs):
        req = REAL_WORLD_BATCH[i]
        sai = calculate_sai(output)
        status = output.status
        statuses[status] = statuses.get(status, 0) + 1
        levels[output.level] = levels.get(output.level, 0) + 1
        if status == "blocked":
            blocked += 1
        total_usd += output.pricing.get("subtotal_total_usd", 0)

        panel_count = output.bom.get("panel_count", 0)
        total = output.pricing.get("subtotal_total_usd", 0)

        print(f"  [{i+1:2d}] {req.get('client_name', '?'):20s} | "
              f"SAI={sai.score:5.1f} | "
              f"SRE={output.sre.get('score', 0):3d} | "
              f"Level={output.level:22s} | "
              f"Status={status:15s} | "
              f"Panels={panel_count:3d} | "
              f"${total:>9.2f}")

    print()
    print("-" * 80)
    print(f"STATUS DISTRIBUTION:  {json.dumps(statuses)}")
    print(f"LEVEL DISTRIBUTION:   {json.dumps(levels)}")
    print(f"BLOCKING RATE:        {blocked}/{len(outputs)} ({blocked/len(outputs)*100:.1f}%)")
    print(f"TOTAL QUOTED:         ${total_usd:,.2f}")

    # SAI Summary
    sai_summary = calculate_batch_sai(outputs)
    print()
    print(f"SAI AVERAGE:          {sai_summary['average']}")
    print(f"SAI MIN/MAX:          {sai_summary['min']} / {sai_summary['max']}")
    print(f"SAI PASS RATE:        {sai_summary['pass_rate']}%")
    print(f"GRADE DISTRIBUTION:   {json.dumps(sai_summary['grade_distribution'])}")

    # Run regression suite
    print()
    print("=" * 80)
    print("REGRESSION SUITE")
    print("=" * 80)
    reg = run_regression_suite()
    print(f"Total: {reg['total']} | Passed: {reg['passed']} | Failed: {reg['failed']} | Rate: {reg['pass_rate']}%")
    for r in reg["results"]:
        mark = "PASS" if r["passed"] else "FAIL"
        print(f"  [{mark}] {r['test_id']} - {r['description'][:60]}")
        if r["failures"]:
            for f in r["failures"]:
                print(f"         -> {f}")

    # Run stress test
    print()
    print("=" * 80)
    print("STRESS TEST")
    print("=" * 80)
    stress = run_stress_test()
    print(f"Processed: {stress.processed}/{stress.total_requests}")
    print(f"Blocked: {stress.blocked} ({stress.blocking_rate:.1f}%)")
    print(f"Errors: {stress.error_count}")
    print(f"Avg SAI: {stress.avg_sai:.1f} | Min: {stress.min_sai:.1f} | Max: {stress.max_sai:.1f}")
    print(f"SAI Pass Rate: {stress.sai_pass_rate:.1f}%")
    print(f"Avg Time: {stress.avg_processing_ms:.2f}ms | Max: {stress.max_processing_ms:.2f}ms")


if __name__ == "__main__":
    main()
