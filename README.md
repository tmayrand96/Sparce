# 📊 Sparce AI — Module GAR (Gestion des activités de remplacement)

**Documentation Produit & Procédure Opérationnelle Standard (POS / SOP)**  
**Public cible :** Gestionnaires d'opérations, planificateurs d'horaires, analystes RH et Direction des Ressources Technologiques et Informationnelles (DRTI).

---

## 🎯 Objectif Opérationnel

**Sparce AI (Module GAR)** est une solution d'aide à la décision et d'optimisation des effectifs. Cette plateforme automatise la réconciliation entre les données de présence réelles et les cibles opérationnelles, détecte les écarts critiques par quart de travail et génère des livrables stratégiques d'arbitrage et d'affectation destinés aux Ressources Humaines.

---

## 🔄 Architecture du Flux Opérationnel (Logigramme)

Le diagramme ci-dessous illustre le cycle complet de traitement, de la saisie terrain jusqu'à la génération conditionnelle des rapports décisionnels :

```mermaid
flowchart TD
    %% Styles exécutifs (#0073A9 charte Sparce AI)
    classDef phase fill:#0073A9,stroke:#004d73,stroke-width:2px,color:#ffffff,font-weight:bold;
    classDef step fill:#f4f9fc,stroke:#0073A9,stroke-width:1.5px,color:#1a1a1a;
    classDef engine fill:#eef6fa,stroke:#005b87,stroke-width:2px,stroke-dasharray: 5 5,color:#004d73,font-weight:bold;
    classDef condition fill:#fff8e6,stroke:#d9822b,stroke-width:2px,color:#5c3709,font-weight:bold;
    classDef governance fill:#f3e8fd,stroke:#7b1fa2,stroke-width:2px,color:#4a148c,font-weight:bold;
    classDef output fill:#e6f4ea,stroke:#1e8e3e,stroke-width:2px,color:#0d652d,font-weight:bold;
    classDef api fill:#e0f2f1,stroke:#00796b,stroke-width:2px,stroke-dasharray: 5 5,color:#004d40,font-weight:bold;

    subgraph P1 ["Étape 1 : Extraction et normalisation des présences (SIRH / Gabarit GAR)"]
        A["Extraction des présences effectives<br/>(Virtuo Lourd / Feuilles quotidiennes)"]:::step
        B["Saisie opérationnelle par quart<br/>(JOUR, SOIR, NUIT)"]:::step
        C["Enregistrement normalisé des classeurs :<br/>• JOUR-06-09.xlsx<br/>• SOIR-05-08.xlsx<br/>• NUIT-06-09.xlsx"]:::step
        A --> B --> C
    end

    subgraph P2 ["Étape 2 : Ingestion et moteur déterministe (Mémoire volatile / Zéro persistance)"]
        D["Ouverture de l'interface web<br/>Sparce AI — Module GAR"]:::step
        E["Importation multi-fichiers .xlsx<br/>(Detected Format : Excel Workforce Workbook)"]:::step
        F["Sélection de la période via calendrier interactif<br/>(ex. : 05/11/2026 – 09/11/2026 → Ok ✅)"]:::step
        G["Paramétrage du « Sélecteur de quart »<br/>(JOUR / SOIR / NUIT / Tous les quarts)"]:::step
        H[["⚙️ Moteur de conciliation déterministe (RAM uniquement) :<br/>Présences réelles vs Cibles de ratios départementaux"]]:::engine
        
        D --> E --> F --> G --> H
        F -.->|Filtrage temporel réactif| H
    end

    subgraph P3 ["Étape 3 : Audit visuel (Human-in-the-Loop), Exportation et Extension API"]
        I["🛡️ Contrôle de conformité obligatoire (Human-in-the-Loop) :<br/>Validation visuelle des écarts nets par l'agent administratif"]:::governance
        J{"Portée choisie dans le<br/>« Sélecteur de quart » ?"}:::condition
        K["Affichage ciblé des écarts<br/>pour le quart unique (JOUR, SOIR ou NUIT)"]:::output
        L["Déverrouillage et exportation directe :<br/>📥 Download Topo 24h (Synthèse Markdown multi-quarts)"]:::output
        M[["🔌 Connect to API (Extension optionnelle / Clé API institutionnelle ex. Azure OpenAI) :<br/>Génération de rapports détaillés de gestion & extraction de statistiques / KPIs<br/>pour les gestionnaires et coordonnateurs"]]:::api

        H --> I --> J
        J -- "Quart unique (Jour / Soir / Nuit)" --> K
        J -- "« Tous les quarts » sélectionné" --> L
        I -. "Connecteur gouverné (Prêt pour tenant DRTI)" .-> M
    end

    C ==> D
```

---

## 📋 Procédure Opérationnelle Étape par Étape

### Étape 1 : Saisie des données de présence (JOUR, SOIR, NUIT)
1. **Accès aux feuilles quotidiennes :** Ouvrez le classeur de suivi et accédez aux onglets d'entrée journaliers (`LUNDI`, `MARDI`, `SAMEDI`, etc.).
2. **Saisie opérationnelle :** Renseignez les données de présence effectives pour le quart de travail correspondant.
3. **Nomenclature d'enregistrement :** Enregistrez systématiquement les classeurs selon la convention normalisée afin d'assurer l'ingestion multi-quarts :
   * `JOUR-XX-XX.xlsx`
   * `SOIR-XX-XX.xlsx`
   * `NUIT-XX-XX.xlsx`

---

### Étape 2 : Importation et traitement dans Sparce AI (Module GAR)
1. **Lancement :** Ouvrez l'application web **Sparce AI — Module GAR**.
2. **Ingestion des fichiers :** Cliquez sur le bouton **Importer** et sélectionnez simultanément ou individuellement vos classeurs `.xlsx` (Jour, Soir, Nuit).
3. **Configuration du rapport (Volet de navigation latéral) :**
   * **Sélecteur de date(s) :** Sélectionnez la période cible. Le moteur exécute immédiatement et automatiquement le rapprochement *Présences vs Cibles*.
   * **Sélecteur de quart :** Filtrez sur un quart précis (`JOUR`, `SOIR`, `NUIT`) ou sélectionnez **`Tous les quarts`** pour une consolidation sur 24 heures. Le recalcul matriciel s'opère instantanément à chaque changement de sélection.

---

### Étape 3 : Interrogation et génération du conseil décisionnel
1. **Analyse interactive :** Utilisez le volet d'analyse / invite de commande de Sparce AI pour interroger directement les données chargées (identification des déficits d'effectifs, détection des goulots d'étranglement et points de friction opérationnels).
2. **Optimisation et arbitrage RH :** Cliquez sur le bouton **`Generate Personalized Workforce Report`** pour exécuter le moteur d'optimisation et produire les recommandations structurées d'arbitrage et de réaffectation.
3. **Exportation du bilan consolidé (Conditionnel) :**
   * Lorsque le **Sélecteur de quart** est positionné sur **`Tous les quarts`**, l'interface active l'option d'exportation globale.
   * Cliquez sur **Télécharger le rapport « Topo 24h – global »** pour extraire la synthèse complète couvrant l'ensemble du cycle de 24 heures.

---

## 🏛️ Gouvernance & Valeur Ajoutée (DRTI / Gestion Opérationnelle)

| Dimension | Bénéfice Opérationnel |
| :--- | :--- |
| **Intégrité des données** | Ingestion directe des classeurs `.xlsx` originaux sans manipulation intermédiaire ni perte de formules. |
| **Réactivité temps réel** | Recalcul dynamique des écarts *Présences vs Cibles* dès l'ajustement du **Sélecteur de date(s)** ou du **Sélecteur de quart**. |
| **Affichage contextuel intelligent** | Le livrable **« Topo 24h – global »** est verrouillé tant que la vue consolidée **« Tous les quarts »** n'est pas active, éliminant tout risque d'exportation partielle ou biaisée. |
| **Standardisation RH** | Production homogène des recommandations d'affectation via le moteur **Generate Personalized Workforce Report**. |

---
*Web app designed and optimized by Tristan Mayrand*
