Je travaille sur la taxonomie pragmatique des messages reçus par
un assistant personnel à mémoire persistante (single-user, long
terme). Une première version (V1) m'a été proposée par un autre
LLM, je te la colle plus bas. Je veux que tu la critiques en
profondeur sur 5 dimensions précises, et que tu proposes une V2
améliorée.

CONTEXTE PRODUIT
- Assistant personnel local pour un seul utilisateur (pas de
  multi-tenant).
- Mémoire persistante avec attachement de "messages" à des
  "intents" (tâches/projets durables) ou enregistrement de
  faits/épisodes.
- Comportements actuels distincts : ATTACH (rattacher un message
  à un intent existant), CREATE (nouvel intent), STORE_FACT
  (mémoire factuelle), réponse conversationnelle simple,
  recherche web, etc.
- Le but de la taxonomie est de router le message en amont vers
  le bon comportement, AVANT le matching d'intent.

LA V1 À CRITIQUER

[colle ici la taxonomie V1 complète que Gemini t'avait fournie,
de la section "1. Évaluation des 4 catégories initiales"
jusqu'à "6. Observation structurante"]

DIMENSIONS DE CRITIQUE ATTENDUES (réponds chacune explicitement)

1. MUTUELLE EXCLUSIVITÉ. La V1 reconnaît que les catégories
   ne sont pas exclusives mais reste sur une classification
   dure. Faut-il basculer sur un classifieur probabiliste avec
   scores par catégorie ? Quels seraient les coûts/bénéfices
   pour un assistant single-user ? Quelles règles de tie-break
   utiliser quand deux catégories ont des scores proches ?

2. CATÉGORIES E (commande système) vs I (feedback agent). Sont-elles
   réellement distinctes du point de vue du comportement attendu,
   ou est-ce une distinction syntaxique (impératif vs descriptif)
   qui ne mérite pas deux catégories ? Si fusion, quel libellé ?

3. AXES OUBLIÉS. La V1 traite l'axe pragmatique. Quels autres
   axes orthogonaux faut-il croiser pour un routing complet ?
   Au moins :
   - Multimodalité (texte / image / voix / fichier) — comment
     l'intégrer sans démultiplier les catégories ?
   - Temporalité (immédiat / différé / récurrent / passé) —
     "rappelle-moi demain de..." appartient à quelle catégorie
     pragmatique + comment porter le différé ?
   - Sensibilité (info banale / info sensible type code/santé)
     — pertinent pour la persistence et la rétrieval ?

4. CATÉGORIE D (mémoriel pur) sous-spécifiée. Distinguer mémoire
   FACTUELLE (durée infinie, type "code portail 9041") vs
   ÉPISODIQUE (datée, type "aujourd'hui j'ai semé des carottes",
   pertinente pour rattachement à un intent existant). Cette
   distinction change-t-elle le comportement de stockage ? De
   recherche ?

5. CAS LIMITES À AJOUTER. La V1 propose 6 cas frontaliers. Trouve
   au moins 3 cas frontaliers supplémentaires non couverts, en
   particulier :
   - Messages multi-segment (un seul tour qui contient mémoire
     + question + commande).
   - Messages négatifs ou correctifs ("ce n'est pas ce que je
     voulais").
   - Messages sans intention claire (digression, hors-sujet).

LIVRABLE ATTENDU

(a) Réponse point par point aux 5 dimensions ci-dessus, prose
    dense, pas de bullets gratuits.
(b) Une V2 de la taxonomie complète (catégories finales,
    définitions, critères de décision), différenciée de la V1
    par les ajouts/fusions/clarifications justifiés.
(c) Un mini-tableau de décision : pour chaque catégorie V2,
    quel comportement par défaut côté assistant (ATTACH /
    CREATE / STORE_FACT / réponse simple / autre) et quelle
    persistance (transitoire / session / longue durée).

Pas de code dans cette réponse. Réfléchis comme un architecte
système, pas comme un développeur. Réponds en français.

voici la v1 :
## 1. Évaluation des 4 catégories initiales

### Mutuelle exclusivité

Elles **ne sont pas totalement exclusives** en l’état, car elles mélangent deux axes différents :

* **axe pragmatique** : que doit faire l’assistant ?
* **axe sémantique** : de quoi parle le message ?

Exemples de chevauchement :

* *« J’ai planté des tomates »*
  → information mémorielle
  → peut implicitement demander un suivi
  → peut aussi être conversationnel.

* *« Vu ma collection d’huiles essentielles… »*
  → demande informative **mais** contextualisée → proche d’un intent actionnable.

Conclusion : les catégories sont bonnes comme **première stratification**, mais elles doivent être complétées par des classes supplémentaires pour couvrir le spectre réel des interactions.

---

### Exhaustivité

Non exhaustive. Plusieurs classes importantes manquent pour un assistant à mémoire persistante :

* commandes système / contrôle d’agent
* gestion explicite de la mémoire
* clarification / réparation conversationnelle
* réflexion non directive
* feedback sur l’assistant

---

## 2. Taxonomie proposée (niveau pragmatique)

Classification orientée **comportement attendu de l’agent**.

### A. INTENT ACTIONNABLE

**Définition**
L’utilisateur attend une aide opérationnelle, un plan, une décision, ou un accompagnement continu.

**Critère clé** : nécessite un **état de tâche actif**.

**Exemples**

* « Aide-moi à organiser un potager sur 20 m² »
* « Planifie un road-trip de 5 jours dans le Vercors »
* « J’ai une erreur I²C intermittente, aide-moi à la diagnostiquer »
* « Donne-moi un programme pour reprendre la course »
* « Voici mon frigo, propose des repas pour la semaine »

---

### B. DEMANDE INFORMATIVE

**Définition**
Recherche de connaissance ou d’explication sans attente de suivi.

**Critère clé** : réponse complète possible en un tour.

**Exemples**

* « Quelle différence entre /hot et /best sur Reddit ? »
* « Combien de temps se conserve le saumon mariné ? »
* « Comment fonctionne une douche à l’italienne ? »
* « Qu’est-ce que l’IPM dans un capteur d’image ? »
* « Quels arbres poussent bien en climat alpin ? »

---

### C. THÈME CONVERSATIONNEL / SOCIAL

**Définition**
Interaction relationnelle ou méta-discursive, sans objectif opérationnel.

**Exemples**

* « Salut »
* « Tu me décrirais comment ? »
* « On parlait de quoi déjà ? »
* « Dis-moi un fait amusant »
* « Tu préfères Linux ou Windows ? »

---

### D. MÉMORIEL PUR

**Définition**
Transmission d’information destinée à la persistance.

**Critère clé** : **aucune action attendue** hors enregistrement.

**Exemples**

* « Code portail : 9041 »
* « J’ai semé des carottes aujourd’hui »
* « Mon chat s’appelle Orion »
* « Nouveau serveur : IP 192.168.1.42 »
* « Début du jeûne intermittent le 3 mai »

---

## 3. Catégories manquantes essentielles

### E. COMMANDE SYSTÈME / CONTRÔLE D’AGENT

Interaction dirigée vers le fonctionnement de l’assistant lui-même.

**Exemples**

* « Oublie cette information »
* « Réinitialise la conversation »
* « Passe en mode concis »
* « Ne mémorise plus mes messages techniques »
* « Montre ce que tu sais sur moi »

Raison d’existence : comportement totalement différent du traitement conversationnel.

---

### F. GESTION EXPLICITE DE MÉMOIRE

Sous-classe distincte du mémoriel pur.

Ici l’utilisateur **manipule la mémoire existante**.

**Exemples**

* « Corrige : je n’habite plus Lyon »
* « Supprime l’adresse que je t’ai donnée »
* « Mets à jour : mon nouveau job commence lundi »
* « Classe ça comme information professionnelle »
* « N’utilise plus cette préférence »

Différence clé :

* D = ajout passif
* F = modification du modèle interne

---

### G. CLARIFICATION / RÉPARATION CONVERSATIONNELLE

Messages servant à restaurer la compréhension.

**Exemples**

* « Non, je parlais du capteur B, pas du A »
* « Reformule plus simplement »
* « Tu as mal compris »
* « Je voulais dire en extérieur »
* « Ignore mon dernier message »

Important pour éviter la pollution mémorielle.

---

### H. RÉFLEXION À VOIX HAUTE / EXTERNALISATION COGNITIVE

L’utilisateur pense devant l’agent sans demander d’action directe.

Très fréquent dans un assistant personnel long terme.

**Exemples**

* « J’hésite à changer de travail »
* « Je me demande si je devrais réduire mes projets »
* « J’ai l’impression de manquer de focus »
* « Peut-être que je devrais automatiser ça »
* « Je réfléchis à déménager en montagne »

Différence avec conversationnel :
→ contenu introspectif pouvant devenir ultérieurement actionnable ou mémoriel.

---

### I. FEEDBACK SUR L’ASSISTANT

Évaluation ou calibration du comportement.

**Exemples**

* « Tes réponses sont trop longues »
* « Ça c’était utile »
* « Arrête les emojis »
* « Tu fais trop d’hypothèses »
* « Continue comme ça »

Critique pour l’adaptation long terme.

---

## 4. Liste finale des catégories

1. Intent actionnable
2. Demande informative
3. Thème conversationnel/social
4. Mémoriel pur
5. Commande système / contrôle d’agent
6. Gestion explicite de mémoire
7. Clarification / réparation conversationnelle
8. Réflexion à voix haute / externalisation cognitive
9. Feedback sur l’assistant

---

## 5. Cas frontaliers et règles de décision

### Cas 1 — Déclaration factuelle ambiguë

**« J’ai planté des tomates »**

Peut être :

* mémoriel pur
* intent actionnable implicite
* réflexion personnelle

**Heuristique pragmatique**

Priorité :

1. question implicite détectable → ACTIONNABLE
2. indication temporelle personnelle → MÉMORIEL
3. ton narratif → RÉFLEXION

---

### Cas 2 — Question contextualisée

**« Vu mon potager, quelles variétés planter ? »**

→ informative **ou** actionnable.

Décision :

* réponse unique → INFORMATIVE
* suivi attendu → ACTIONNABLE

Indice : présence d’un projet continu.

---

### Cas 3 — Information + attente cachée

**« Mon PC fait un bruit étrange »**

Surface : déclaration
Intention réelle : aide.

Principe :

> priorité à l’intention opérationnelle probable plutôt qu’à la forme grammaticale.

---

### Cas 4 — Mémoire déguisée

**« Note que je travaille désormais en remote »**

→ gestion explicite de mémoire, pas mémoriel pur.

---

### Cas 5 — Réflexion devenant tâche

**« J’aimerais être plus sportif… »**

Initialement : réflexion
Si suivi demandé → transition vers actionnable.

---

### Cas 6 — Conversation vs feedback

**« Tes réponses sont longues »**

Pas social → feedback agent.

---

## 6. Observation structurante

Un assistant personnel persistant fonctionne mieux si la taxonomie distingue :

* **interaction avec le monde** (actionnable)
* **interaction avec la connaissance** (informatif)
* **interaction sociale**
* **interaction avec la mémoire**
* **interaction avec l’agent**
* **interaction cognitive interne de l’utilisateur**

Tes 4 catégories couvrent seulement les trois premières dimensions. Les ajouts complètent le modèle comportemental nécessaire à un agent long-terme single-user.


##### v2 version gemini :

### Évaluation architecturale et critique de la taxonomie V1

**1. Mutuelle exclusivité et approche probabiliste**
La V1 échoue à maintenir une exclusivité mutuelle car elle traite le message comme une entité atomique à intention unique, ce qui est une erreur de conception pour un assistant à mémoire longue. Dans un système single-user, l'implémentation d'un classifieur probabiliste avec un vecteur de scores par catégorie est indispensable. Le bénéfice majeur réside dans le "multi-routing" : un message comme "J'ai fini le rapport, rappelle-moi d'appeler Marc" possède un score élevé en *Mémoriel* (clôture de tâche) et en *Actionnable* (création de rappel). Les coûts computationnels d'un scoring multidimensionnel sont négligeables par rapport au gain de fiabilité du graphe de mémoire. Pour les cas de litige (scores proches), la règle de tie-break doit suivre une hiérarchie de "risque d'attrition" : l'Actionnable prime sur le Mémoriel, qui prime sur l'Informatif. En dernier recours, l'assistant doit favoriser le comportement qui enrichit le contexte de l'utilisateur plutôt que celui qui fournit une réponse générique.

**2. Catégories E (Commande) vs I (Feedback)**
Bien qu'elles partagent une nature méta-discursive, ces catégories doivent rester distinctes pour des raisons de cycle de vie logiciel. La Commande système (E) est une instruction impérative à exécution immédiate sur l'état de l'application (ex: "supprime les logs"). Le Feedback agent (I) est une donnée de calibration pour l'alignement du modèle de langage ou l'ajustement du "système prompt" à long terme. Fusionner ces deux classes reviendrait à confondre le pilotage du moteur et le réglage des rétroviseurs. Une distinction syntaxique cache ici une distinction fonctionnelle profonde : l'un modifie le contenant (l'assistant), l'autre modifie le comportement (le style ou la pertinence).

**3. Axes orthogonaux : Multimodalité, Temporalité et Sensibilité**
L'intégration de la multimodalité ne doit pas créer de nouvelles catégories mais agir comme un modificateur d'intent (un "Payload Tag"). Un fichier image peut supporter aussi bien une demande informative qu'une commande mémorielle. La temporalité, en revanche, est un axe de routing critique : le "différé" (rappelle-moi demain) transforme une intention immédiate en une tâche planifiée dans le calendrier de l'agent, nécessitant un état d'attente. Enfin, l'axe de sensibilité est le pivot de la politique de persistance locale. Une information "Sensible" (santé, finance, codes) doit déclencher des protocoles de stockage chiffré ou de rétention limitée, indépendamment de sa nature pragmatique. Un assistant mémoriel qui traite un code de carte bleue comme un nom de chat échoue sur le plan de la sécurité structurelle.

**4. Mémoriel Factuel vs Épisodique**
La sous-spécification de la catégorie D ignore la structure cognitive humaine que l'assistant cherche à simuler. Le stockage factuel (sémantique) requiert une structure de type "Key-Value Store" ou base de connaissances indexée pour une récupération exacte et universelle. Le stockage épisodique (chronologique) nécessite un index temporel et contextuel ("Journal") où la valeur de l'information est liée à sa date et aux événements environnants. Dans le premier cas, la recherche est par mot-clé ou entité ; dans le second, elle est par similarité de situation ou fenêtre temporelle. Ne pas distinguer ces deux flux empêche l'assistant de comprendre que "Le code est 1234" écrase une vérité précédente, alors que "J'ai mangé une pomme" s'ajoute simplement à une liste d'événements.

**5. Cas limites supplémentaires**
Trois nouveaux cas frontaliers complexifient le routing. Les messages multi-segments, d'abord, où l'utilisateur concatène des intentions ("Note ça, et d'ailleurs, pourquoi le ciel est bleu ?"), imposent une segmentation pré-classification. Les messages correctifs ou négatifs ("Non, pas ça", "Tu te trompes") ne sont ni des commandes système ni des clarifications, mais des actes de réparation d'état qui doivent invalider la dernière opération de mémoire. Enfin, les messages de maintien de contact ou de suspension ("Attends", "Euh...", "Je réfléchis") n'ont aucune intention pragmatique sinon de maintenir la session ouverte ; ils doivent être routés vers un comportement de veille passive sans déclencher de calcul de mémoire ou de recherche web.

---

### V2 de la Taxonomie Pragmatique

| Code | Catégorie | Définition | Critère de décision |
| :--- | :--- | :--- | :--- |
| **OP** | **Opérationnel** | Action concrète, planification ou gestion de tâche. | Présence d'un verbe d'action futur ou d'un objectif mesurable. |
| **IN** | **Épistémique** | Recherche de connaissance générale ou ponctuelle. | Question fermée ou demande d'explication décorrélée de l'utilisateur. |
| **MF** | **Mémoire Factuelle** | Enregistrement de constantes, règles ou données pérennes. | Information "statique" (codes, noms, préférences, adresses). |
| **ME** | **Mémoire Épisodique** | Journalisation d'événements, d'états d'âme ou d'actions passées. | Information "ancrée" (narration, chronologie, suivi de santé). |
| **MT** | **Méta / Système** | Pilotage direct de l'agent ou feedback sur ses performances. | Instruction impérative technique ou jugement sur la réponse. |
| **RP** | **Réparation** | Correction d'une erreur de l'agent ou annulation d'une action. | Négation explicite ou rectification d'un fait précédemment stocké. |
| **CO** | **Cognitif / Social** | Réflexion à voix haute, digression ou interaction phatique. | Absence d'objectif clair ; contenu introspectif ou relationnel. |

---

### Tableau de décision et comportements système

| Catégorie V2 | Comportement par défaut | Persistance cible | Stratégie de stockage |
| :--- | :--- | :--- | :--- |
| **OP (Opérationnel)** | **CREATE / ATTACH** | Longue durée | Graphe d'Intents / Calendrier |
| **IN (Épistémique)** | **Web Search / RAG** | Transitoire | Cache de session uniquement |
| **MF (Factuelle)** | **STORE_FACT** | Infinie | Base de connaissances (Key-Value) |
| **ME (Épisodique)** | **STORE_FACT (Log)** | Longue durée | Vector Store chronologique |
| **MT (Méta)** | **System Command** | Session / Profil | Mise à jour des préférences agent |
| **RP (Réparation)** | **DELETE / UPDATE** | Immédiate | Modification atomique de la DB |
| **CO (Cognitif)** | **Réponse simple** | Session | Historique de chat (contexte court) |

**Indice de Confiance (Architecture) : 95%**
**Sources :** Principes de design des architectures d'agents autonomes (AutoGPT/BabyAGI) et modèles de mémoire cognitive (ACT-R).


##### v2 version deepseek :

Voici une critique architecturale de la V1 et une V2 repensée pour un assistant personnel single-user à mémoire persistante.

---

### 1. MUTUELLE EXCLUSIVITÉ

La V1 reconnaît l’absence d’exclusivité mais conserve une classification dure avec des règles de priorité ad hoc. Dans un assistant single-user longue durée, le classifieur probabiliste apporte un bénéfice réel : il permet de traiter les messages intrinsèquement mixtes (une déclaration personnelle qui flirte avec l’actionnable tout en étant un fait mémorisable) sans décision arbitraire précoce. Le coût principal est l’inférence supplémentaire et la nécessité d’étalonner des seuils de confiance, mais la persistance locale autorise un modèle léger (type petit transformeur ou régression logistique sur traits) sans latence rédhibitoire. En pratique, on peut fournir un vecteur de scores par catégorie, puis déclencher le routage en fonction du score maximal. Lorsque deux scores sont à moins de 0,1 d’écart, on bascule sur une demande de clarification brève (« Tu veux que j’enregistre ça ou que je t’aide ? »). Les règles de tie-break statiques restent utiles en fallback : une intention opérationnelle (tâche) l’emporte toujours sur le mémoriel épisodique si le seuil est ambigu, car l’utilisateur peut toujours rattraper l’oubli d’un souvenir mais pas celui d’une action immédiate. À l’inverse, une commande système explicite prime sur tout feedback latent. Le choix probabiliste renforce l’adaptation au style de l’utilisateur au fil du temps, un atout critique en single-user.

### 2. CATÉGORIES E (COMMANDE SYSTÈME) ET I (FEEDBACK AGENT)

Ces deux classes concernent toutes les deux l’agent lui-même, mais la séparation repose sur une distinction syntaxique (impératif vs. évaluatif) plutôt que sur une différence comportementale fondamentale. Une commande comme « passe en mode concis » exige une action immédiate de reconfiguration, tandis qu’un feedback comme « tes réponses sont trop longues » appelle un ajustement progressif. Pour autant, le routage amont n’a pas besoin de deux catégories disjointes : l’une et l’autre déclenchent une analyse de l’intention vers le « contrôle de l’agent », charge à un sous-module de distinguer la reconfiguration immédiate de l’enregistrement de préférence. La fusion sous l’intitulé **Contrôle et feedback agent** clarifie l’architecture, réduit l’ambiguïté de frontière (ex. « Arrête les emojis » est à la fois feedback et commande) et évite la multiplication des classes. Dans la V2, on conserve le distinguo au niveau de la décision interne (exécution vs journalisation), mais la taxonomie de routage n’a qu’une seule porte d’entrée.

### 3. AXES OUBLIÉS

La V1 ignore des dimensions orthogonales qui impactent pourtant le comportement sans relever de la pragmatique de surface. Leur intégration passe par une séparation nette entre **classe pragmatique** (le « pourquoi » du message) et **attributs transversaux** (modality, temporalité, sensibilité) attachés en métadonnées.

**Multimodalité** : un message vocal ou une image n’est pas une catégorie pragmatique, c’est un container. Sa prise en compte intervient en prétraitement (transcription, extraction de texte d’image). La classe pragmatique finale est déterminée sur le contenu textuel résultant, sans démultiplier les catégories. Le routage peut néanmoins ajouter un comportement spécifique si la modalité exige un stockage de média (ex. une photo de frigo rattachée à l’intent « cuisine »). L’attribut `media_type` guide cette variante.

**Temporalité** : un message comme « rappelle-moi demain de tailler les rosiers » est une tâche actionnable (INTENT ACTIONNABLE) dotée d’une date d’échéance. L’axe temporel est un paramètre de l’action, pas une catégorie. L’assistant doit extraire une échéance, une récurrence ou un rappel et la stocker dans l’intent. Pour les faits, un « j’ai semé des carottes aujourd’hui » est un mémoriel épisodique horodaté ; l’information temporelle est un champ de la mémoire, pas une classe séparée. Ainsi, la temporalité est un filtre post-routage.

**Sensibilité** : un mot de passe ou une donnée de santé doit déclencher un chiffrement et une exclusion des logs. Cet attribut est détecté par un classifieur de confidentialité parallèle (basé sur regex entités PII, embeddings de vie privée). Il n’a pas à contaminer les catégories pragmatiques. Une information factuelle sensible reste un MÉMORIEL FACTUEL, mais la politique de persistance et d’indexation change.

### 4. CATÉGORIE D (MÉMORIEL PUR) SOUS-SPÉCIFIÉE

La V1 place dans le même panier des énoncés radicalement différents quant au stockage et à la recherche. « Code portail 9041 » est un fait atomique, intemporel, qui doit être stocké de manière relationnelle (clé-valeur ou triplet) et retrouvé par requête exacte. « Aujourd’hui j’ai semé des carottes » est un épisode personnel, daté, dont la pertinence dépend du contexte temporel et du lien avec un projet existant (ex. le potager). Le premier doit déclencher un **STORE_FACT** en base de connaissances factuelles, sans attachement à un intent en cours. Le second appelle naturellement un **ATTACH** à l’intent actif le plus probable (si un projet « potager » est ouvert), ou à défaut un **STORE_EPISODE** indépendant, indexé chronologiquement. La distinction modifie aussi le comportement de recherche : pour une question factuelle (« quel est le code du portail ? »), on interroge le store de faits ; pour une question épisodique (« qu’ai-je fait au jardin en avril ? »), on navigue dans la timeline des épisodes. En conséquence, la V2 éclate D en deux catégories pragmatiques distinctes (Mémoriel factuel, Mémoriel épisodique), le routage aval différant radicalement.

### 5. CAS LIMITES SUPPLÉMENTAIRES

**Message multi-segment** : « Pour le projet potager j’ai mis des tomates. D’ailleurs comment on éloigne les limaces ? Et note que le portail fait 9041. » Ce tour contient un épisode, une question informative et un fait. Aucune catégorie unique ne convient. La taxonomie doit s’appliquer après segmentation du message en énoncés individuels (via détection de frontières par ponctuation et connecteurs). Chaque segment est classé indépendamment, et l’assistant peut enchaîner plusieurs comportements (ATTACH, réponse, STORE_FACT) dans la même réponse. La V2 précise que le routage opère sur une unité pragmatique élémentaire, pas nécessairement sur le tour complet.

**Message correctif ou négatif** : « Ce n’est pas ce que je voulais » ou « Non, 9042 pas 9041 » ne sont ni une simple clarification conversationnelle ni une gestion explicite de mémoire standard. Le premier cas vise à réparer l’interprétation de l’assistant (ex. mauvais intent rattaché) ; il doit annuler la dernière action de mémoire et redemander l’intention. Le second corrige un fait précédent. Dans les deux cas, la catégorie **Gestion explicite de mémoire** est la plus proche, mais enrichie d’un sous-mode « correction rétroactive ». Si le message contredit un stockage récent, le système annule l’ancien enregistrement et applique la mise à jour, plutôt que d’ajouter un doublon. La taxonomie V2 traite ces cas comme des variantes de la gestion de mémoire, sans créer de catégorie ad hoc.

**Message sans intention claire** : « Bref, il fait beau » en plein milieu d’une session sur les courses. Ni tâche, ni fait mémorable, ni réparation. Le classifier probabiliste produira des scores plats, le score maximal restant sous le seuil de confiance (par ex. < 0,5 pour toute classe). L’assistant peut alors adopter une réponse sociale minimale et ne rien persister. La V2 prévoit un comportement par défaut **conversationnel** en cas d’ambiguïté totale, avec une persistance transitoire (rien n’est mémorisé sauf marqueur de contexte de session pour éviter les sauts de sujet).

---

## V2 DE LA TAXONOMIE PRAGMATIQUE

Les catégories finales, leurs définitions et leurs critères de décision sont les suivants. Les fusions et scissions par rapport à la V1 sont justifiées dans le corps.

**1. Tâche actionnable** – L’utilisateur attend une aide opérationnelle, un plan, un suivi continu. Critère : nécessite la création d’un intent actif ou l’attachement à un intent existant. Exemple : « Aide-moi à planifier un road trip en Bretagne », « Diagnostique cette erreur I²C ».

**2. Demande informative** – Recherche de connaissance sans attente de suivi tâche. Critère : une réponse complète peut être fournie en un tour, sans création d’intent. Exemple : « Quelle est la différence entre /hot et /best sur Reddit ? ».

**3. Conversationnel / social** – Interaction relationnelle ou digression sans objectif opérationnel ni mémoriel explicite. Critère : absence de demande de stockage ou d’action. Exemple : « Salut », « Tu préfères Linux ou Windows ? ».

**4. Mémoriel factuel** – Transmission d’un fait atomique destiné à une persistance intemporelle. Aucune action attendue hors l’enregistrement factuel. Exemple : « Code portail 9041 », « Mon groupe sanguin O+ ».

**5. Mémoriel épisodique** – Récit d’un événement personnel daté explicitement ou implicitement. Critère : se rattache naturellement à un projet en cours ou constitue un souvenir chronologique indépendant. Exemple : « J’ai semé des carottes aujourd’hui », « Ce matin j’ai couru 5 km ».

**6. Contrôle et feedback agent** – Message qui modifie le comportement de l’assistant ou évalue ses réponses. Fusion des ex-E et I. Exemple : « Passe en mode concis », « Oublie cette information » (ici frontière avec gestion mémoire, mais l’intention porte sur l’agent), « Tes réponses sont trop longues ».

**7. Gestion explicite de mémoire** – Manipulation directe de la mémoire persistante : correction, suppression, mise à jour, réorganisation. Critère : l’utilisateur parle d’une information déjà stockée. Exemple : « Corrige : je n’habite plus Lyon », « Supprime l’adresse que je t’ai donnée », « Note que le code est en fait 9042 ».

**8. Réparation conversationnelle** – Message visant à restaurer la compréhension mutuelle immédiate, sans modifier la mémoire long terme (sauf annulation éventuelle). Distinct de la gestion mémoire car l’objet est l’interprétation de l’échange, non le stock. Exemple : « Non, je parlais du capteur B », « Reformule plus simplement ».

**9. Réflexion à voix haute / externalisation cognitive** – Pensée introspective exprimée sans demande opérationnelle directe, souvent hésitante ou exploratoire. Critère : l’utilisateur parle de soi, de ses doutes, de ses projets à l’état embryonnaire. Exemple : « J’hésite à changer de boulot », « Peut-être que je devrais automatiser ça ».

Changements majeurs : fusion E+I (dimension 2), scission D en factuel/épisodique (dimension 4), et explicitation que les messages multi-segments sont segmentés en entrée. La réparation conversationnelle reste distincte de la gestion mémoire après analyse de la frontière corrective (dimension 5).

---

## TABLEAU DE DÉCISION (comportement par défaut et persistance)

| Catégorie V2                    | Comportement par défaut de l’assistant       | Persistance                         |
|---------------------------------|----------------------------------------------|-------------------------------------|
| Tâche actionnable               | CREATE ou ATTACH selon l’intent ouvert       | Longue durée (intent)              |
| Demande informative             | Réponse simple (recherche web si nécessaire) | Transitoire (non persistée)        |
| Conversationnel / social        | Réponse relationnelle brève                  | Transitoire (sauf contexte session)|
| Mémoriel factuel                | STORE_FACT                                   | Longue durée (base de faits)       |
| Mémoriel épisodique             | ATTACH si intent pertinent, sinon STORE_EPISODE | Longue durée (timeline mémoire) |
| Contrôle et feedback agent      | Exécution de la commande ou enregistrement du feedback | Longue durée (préférences) |
| Gestion explicite de mémoire    | Opération CRUD sur la mémoire                | Longue durée (mise à jour)         |
| Réparation conversationnelle    | Clarification / correction de l’échange      | Aucune (sauf annulation de la dernière action) |
| Réflexion à voix haute          | Reformulation empathique, proposition d’approfondissement | Aucune par défaut (sauf si l’utilisateur demande une mémorisation) |

Cette V2 conserve une stratification primaire pragmatique, délègue les axes othogonaux à des attributs, et adapte le routage aux spécificités d’une mémoire personnelle durable.