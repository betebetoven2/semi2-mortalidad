import download_ine
import download_oms
import download_ca

print("=" * 50)
print("INGESTA SEMI2 — INICIO")
print("=" * 50)

print("\n--- INE Guatemala ---")
download_ine.run()

print("\n--- WHO / OMS ---")
download_oms.run()

print("\n--- Centroamérica ---")
download_ca.run()

print("\n" + "=" * 50)
print("INGESTA COMPLETA")
print("=" * 50)
