if st.button("💾 Salva Modifiche Accredito", key="btn_salva_accredito"):
        try:
          # Carichiamo tutti i pagamenti dal database
          df_db = carica_pagamenti_da_supabase()
          
          if df_db.empty:
            st.warning("Nessun dato presente nel database.")
          else:
            # 1. Aggiorniamo nel dataframe generale i valori modificati nell'editor per il condomino attivo
            for _, row_edited in df_editato.iterrows():
              id_riga = int(row_edited["id"])
              val_acc = row_edited["accredito"]
              nuovo_accredito = float(val_acc) if val_acc is not None and str(val_acc).strip() != "" else 0.0
              df_db.loc[df_db["id"] == id_riga, "accredito"] = nuovo_accredito

            # 2. Eseguiamo il ricalcolo sequenziale SOLO per il condomino attivo attualmente visualizzato
            sub_indices = df_db[df_db["condominio"] == cond_attivo].sort_values(by="id", ascending=True).index
            
            riporto_precedente = 0.0
            for i, idx in enumerate(sub_indices):
              if i > 0:
                df_db.loc[idx, "accredito"] = round(riporto_precedente, 2)
              
              accredito_corrente = float(df_db.loc[idx, "accredito"])
              importo_pagato = float(df_db.loc[idx, "importo_pagato"])
              importo_da_pagare = float(df_db.loc[idx, "importo_da_pagare"])
              
              # Formula: riporto = importo_pagato + accredito - importo_da_pagare
              riporto_corrente = round(importo_pagato + accredito_corrente - importo_da_pagare, 2)
              df_db.loc[idx, "riporto"] = riporto_corrente
              
              riporto_precedente = riporto_corrente

            # 3. Inviamo su Supabase unicamente gli aggiornamenti delle righe appartenenti al condomino attivo
            sub_df_updated = df_db[df_db["condominio"] == cond_attivo]
            for _, row in sub_df_updated.iterrows():
              id_riga = int(row["id"])
              payload_update = {
                  "accredito": float(row["accredito"]),
                  "riporto": float(row["riporto"])
              }
              try:
                supabase.table("pagamenti").update(payload_update).eq("id", id_riga).execute()
              except Exception:
                supabase.table("pagamneti").update(payload_update).eq("id", id_riga).execute()

            st.session_state.pagamenti = carica_pagamenti_da_supabase()
            st.success(f"Modifiche salvate e ricalcolo completato per {cond_attivo}!")
            st.rerun()

        except Exception as e:
          st.error(f"Errore durante il salvataggio: {e}")
