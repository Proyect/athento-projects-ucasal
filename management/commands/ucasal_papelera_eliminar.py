#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = (
        "Marca removed=True en Files de serie='papelera' y doctype='designaciones' "
        "cuando pasaron >15 días desde metadata.designaciones_fecha_rechazo."
    )

    def handle(self, *args, **options):
        from datetime import date, datetime
        from file.models import File

        RETENTION_DAYS = 15
        hoy = date.today()

        # Query EXACTO que vas a usar
        qs = File.objects.filter(serie__name="papelera", doctype__name="designaciones")
        total_qs = qs.count()

        marcados = 0
        omitidos_sin_fecha = 0
        omitidos_formato_invalido = 0

        for fil in qs:
            raw = fil.gmv("metadata.designaciones_fecha_rechazo")
            if not raw:
                omitidos_sin_fecha += 1
                continue

            # Normalización de fecha (prioridad al formato real DD-MM-YYYY)
            fecha = None
            if isinstance(raw, date) and not isinstance(raw, datetime):
                fecha = raw
            elif isinstance(raw, datetime):
                fecha = raw.date()
            elif isinstance(raw, str):
                s = raw.strip()
                # 1) Formato real que tenés en DB: DD-MM-YYYY
                try:
                    fecha = datetime.strptime(s, "%d-%m-%Y").date()
                except ValueError:
                    # 2) Alternativo por si aparece YYYY-MM-DD en algún caso
                    try:
                        fecha = datetime.strptime(s[:10], "%Y-%m-%d").date()
                    except ValueError:
                        fecha = None

            if not fecha:
                omitidos_formato_invalido += 1
                continue

            if (hoy - fecha).days > RETENTION_DAYS:
                fil.removed = True
                fil.save(update_fields=["removed"])
                marcados += 1
                self.stdout.write(f"[OK] {fil.filename} (rechazo={fecha.isoformat()}) → removed=True")

        resumen = (
            f"Total en query={total_qs} | marcados={marcados} | "
            f"sin_fecha={omitidos_sin_fecha} | formato_invalido={omitidos_formato_invalido}"
        )
        self.stdout.write(self.style.SUCCESS(resumen))