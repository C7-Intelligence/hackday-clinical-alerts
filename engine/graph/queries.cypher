// Clinical Alert Triage: Neo4j Cypher (CONTRACT §6)
// SYNTHETIC DATA ONLY. Not for clinical use.
//
// Each statement starts with a `// @name <name>` line and ends with `;`. engine/graph/seed.py loads
// statements from this file by name, so what the seed runs is exactly what the skill and the demo run.
//
// Graph model
//   (:Member {id, name, age, sex, memberSince, plan:'All-Inclusive', synthetic:true})
//     -[:HAS_CONDITION]->(:Condition {code, display})
//     -[:TAKES {dose, route, frequency, start}]->(:Medication {name})-[:IN_CLASS]->(:TherapyClass {name})
//     -[:HAS_ALERT {asOf}]->(:Alert:Clinical|Nudge|Informational {id, ruleId, tier, priority, title, asOf})
//   (:TherapyClass)-[:HAS_RISK]->(:Risk {id, risk, monitor, relatedRules})
//   (:Alert)-[:EXPLAINED_BY]->(:Risk)
//
// An alert is linked to a risk only when the member actually takes a medication in that risk's therapy
// class AND the alert's ruleId is in Risk.relatedRules. So a severe-BP alert on a member who isn't on TRT
// isn't blamed on TRT.
//
// Tier labels (:Clinical / :Nudge / :Informational) are extra labels on :Alert, so Neo4j Browser can
// colour alerts by tier (see engine/graph/style.grass).


// ======================================================================================================
// 1. WRITE: the statement the triage-patient skill runs once per triage (via write-neo4j-cypher)
// ======================================================================================================
//
// Idempotent: MERGEs the member, deletes that member's previous alerts, writes the new ones, and links
// each to its risk(s). Re-running a triage never duplicates nodes. An empty $alerts list just clears the
// member's alerts.
//
// Params, built from the engine's TriageResult with jq in the skill:
//
//   python3 .claude/skills/triage-patient/triage.py --patient-id SYN-001 \
//       --data-dir .claude/skills/triage-patient/data > result.json
//   jq '{member: {id: .patientId, name: .patientName, age, sex, memberSince},
//        asOf,
//        alerts: [.alerts[] | {id, ruleId, tier, priority, title}]}' result.json > graph-params.json
//
// Then call write-neo4j-cypher with query = this statement and params = graph-params.json.
// Returns one row: {memberId, alertsWritten, risksLinked}.

// @name write-triage
MERGE (m:Member {id: $member.id})
SET m.name = $member.name,
    m.age = $member.age,
    m.sex = $member.sex,
    m.memberSince = $member.memberSince,
    m.plan = 'All-Inclusive',
    m.synthetic = true,
    m.lastTriagedAsOf = $asOf
WITH m
OPTIONAL MATCH (m)-[:HAS_ALERT]->(old:Alert)
DETACH DELETE old
WITH DISTINCT m
UNWIND $alerts AS a
MERGE (al:Alert {id: a.id})
SET al.ruleId = a.ruleId,
    al.tier = a.tier,
    al.priority = a.priority,
    al.title = a.title,
    al.asOf = $asOf,
    al.synthetic = true
FOREACH (_ IN CASE WHEN a.tier = 'clinical' THEN [1] ELSE [] END | SET al:Clinical)
FOREACH (_ IN CASE WHEN a.tier = 'nudge' THEN [1] ELSE [] END | SET al:Nudge)
FOREACH (_ IN CASE WHEN a.tier = 'informational' THEN [1] ELSE [] END | SET al:Informational)
MERGE (m)-[h:HAS_ALERT]->(al)
SET h.asOf = $asOf
WITH m, al
OPTIONAL MATCH (m)-[:TAKES]->(:Medication)-[:IN_CLASS]->(:TherapyClass)-[:HAS_RISK]->(r:Risk)
WHERE al.ruleId IN r.relatedRules
FOREACH (_ IN CASE WHEN r IS NULL THEN [] ELSE [1] END | MERGE (al)-[:EXPLAINED_BY]->(r))
RETURN $member.id AS memberId, count(DISTINCT al) AS alertsWritten, count(DISTINCT r) AS risksLinked;


// ======================================================================================================
// 2. DEMO COHORT QUERIES (expected results: data/expected-alerts.json -> cohorts)
// ======================================================================================================

// "Which TRT members have a hematocrit problem?"  (short demo)  ->  SYN-001, SYN-002
// @name cohort-trt-hematocrit
MATCH (m:Member)-[:TAKES]->(:Medication)-[:IN_CLASS]->(tc:TherapyClass {name: 'androgen'})
      -[:HAS_RISK]->(r:Risk {id: 'RISK-TRT-ERYTHROCYTOSIS'})<-[:EXPLAINED_BY]-(a:Alert)<-[:HAS_ALERT]-(m)
RETURN DISTINCT m.id AS memberId, m.name AS member, a.tier AS tier, a.title AS alert
ORDER BY memberId, tier;

// "Which GLP-1 members have a kidney or hydration alert?"  ->  SYN-001, SYN-003, SYN-004
// @name cohort-glp1-kidney
MATCH (m:Member)-[:TAKES]->(:Medication)-[:IN_CLASS]->(tc:TherapyClass {name: 'GLP-1 receptor agonist'})
      -[:HAS_RISK]->(r:Risk)<-[:EXPLAINED_BY]-(a:Alert)<-[:HAS_ALERT]-(m)
WHERE r.id IN ['RISK-GLP1-DEHYDRATION', 'RISK-GLP1-AKI']
RETURN DISTINCT m.id AS memberId, m.name AS member, a.tier AS tier, a.title AS alert
ORDER BY memberId, tier;

// Same two cohorts as pictures, for Neo4j Browser (return paths so the graph view lights up the loop
// member -> medication -> therapy class -> risk <- alert <- member).

// @name cohort-trt-hematocrit-graph
MATCH p = (m:Member)-[:TAKES]->(:Medication)-[:IN_CLASS]->(:TherapyClass {name: 'androgen'})
          -[:HAS_RISK]->(r:Risk {id: 'RISK-TRT-ERYTHROCYTOSIS'})<-[:EXPLAINED_BY]-(a:Alert)<-[:HAS_ALERT]-(m)
RETURN p;

// @name cohort-glp1-kidney-graph
MATCH p = (m:Member)-[:TAKES]->(:Medication)-[:IN_CLASS]->(:TherapyClass {name: 'GLP-1 receptor agonist'})
          -[:HAS_RISK]->(r:Risk)<-[:EXPLAINED_BY]-(a:Alert)<-[:HAS_ALERT]-(m)
WHERE r.id IN ['RISK-GLP1-DEHYDRATION', 'RISK-GLP1-AKI']
RETURN p;


// ======================================================================================================
// 3. INVESTOR-FRIENDLY POPULATION QUERIES
// ======================================================================================================

// Open alerts per therapy program (TRT / GLP-1 / Other). A member on both TRT and a GLP-1 counts in both.
// @name alerts-per-program
MATCH (m:Member)
OPTIONAL MATCH (m)-[:TAKES]->(:Medication)-[:IN_CLASS]->(tc:TherapyClass)
WITH m, collect(DISTINCT tc.name) AS classes
WITH m, [p IN [CASE WHEN 'androgen' IN classes THEN 'TRT' END,
               CASE WHEN 'GLP-1 receptor agonist' IN classes THEN 'GLP-1' END] WHERE p IS NOT NULL] AS programs
UNWIND CASE WHEN size(programs) = 0 THEN ['Other'] ELSE programs END AS program
OPTIONAL MATCH (m)-[:HAS_ALERT]->(a:Alert)
RETURN program,
       count(DISTINCT m) AS members,
       count(CASE WHEN a.tier = 'clinical' THEN 1 END) AS clinical,
       count(CASE WHEN a.tier = 'nudge' THEN 1 END) AS nudge,
       count(CASE WHEN a.tier = 'informational' THEN 1 END) AS informational
ORDER BY CASE program WHEN 'TRT' THEN 0 WHEN 'GLP-1' THEN 1 ELSE 2 END;

// Members trending toward a clinical alert: a nudge today whose risk also drives a clinical rule, and no
// clinical alert on that same risk yet. "Call Marcus before he's David."
// @name trending-toward-clinical
MATCH (m:Member)-[:HAS_ALERT]->(a:Nudge)-[:EXPLAINED_BY]->(r:Risk)
WHERE any(rule IN r.relatedRules WHERE rule STARTS WITH 'CLIN-')
  AND NOT EXISTS { (m)-[:HAS_ALERT]->(:Clinical)-[:EXPLAINED_BY]->(r) }
RETURN m.id AS memberId, m.name AS member, a.title AS nudge, r.risk AS risk,
       [rule IN r.relatedRules WHERE rule STARTS WITH 'CLIN-'] AS wouldEscalateTo
ORDER BY memberId;

// Club at a glance: members, and how many need the care team today.
// @name club-overview
MATCH (m:Member)
OPTIONAL MATCH (m)-[:HAS_ALERT]->(a:Alert)
WITH m, collect(a.tier) AS tiers
RETURN count(m) AS members,
       count(CASE WHEN 'clinical' IN tiers THEN 1 END) AS needCareTeamToday,
       count(CASE WHEN 'nudge' IN tiers AND NOT 'clinical' IN tiers THEN 1 END) AS needANudge,
       count(CASE WHEN NOT 'clinical' IN tiers AND NOT 'nudge' IN tiers THEN 1 END) AS allClear;

// The therapy -> risk knowledge map (what the graph knows before any member is triaged).
// @name knowledge-map
MATCH p = (:TherapyClass)-[:HAS_RISK]->(:Risk)
RETURN p;

// Everything about one member, as a picture. Set the member first:  :param memberId => 'SYN-001'
// @name member-360
MATCH p = (m:Member {id: $memberId})-[*1..3]->()
RETURN p;


// ======================================================================================================
// 4. SEED (run by engine/graph/seed.py on Stephen's laptop, not by the skill)
// ======================================================================================================

// @name seed-constraint-member
CREATE CONSTRAINT member_id IF NOT EXISTS FOR (n:Member) REQUIRE n.id IS UNIQUE;
// @name seed-constraint-condition
CREATE CONSTRAINT condition_code IF NOT EXISTS FOR (n:Condition) REQUIRE n.code IS UNIQUE;
// @name seed-constraint-medication
CREATE CONSTRAINT medication_name IF NOT EXISTS FOR (n:Medication) REQUIRE n.name IS UNIQUE;
// @name seed-constraint-therapyclass
CREATE CONSTRAINT therapyclass_name IF NOT EXISTS FOR (n:TherapyClass) REQUIRE n.name IS UNIQUE;
// @name seed-constraint-risk
CREATE CONSTRAINT risk_id IF NOT EXISTS FOR (n:Risk) REQUIRE n.id IS UNIQUE;
// @name seed-constraint-alert
CREATE CONSTRAINT alert_id IF NOT EXISTS FOR (n:Alert) REQUIRE n.id IS UNIQUE;

// Wipe only the demo's labels (used by seed.py --reset).
// @name seed-reset
MATCH (n)
WHERE n:Member OR n:Condition OR n:Medication OR n:TherapyClass OR n:Risk OR n:Alert
DETACH DELETE n;

// Therapy -> risk knowledge from data/therapy-risks.json.  Params: $risks = [{id, therapyClass, risk, monitor, relatedRules}]
// @name seed-risks
UNWIND $risks AS r
MERGE (risk:Risk {id: r.id})
SET risk.risk = r.risk, risk.monitor = r.monitor, risk.relatedRules = r.relatedRules, risk.synthetic = true
MERGE (tc:TherapyClass {name: r.therapyClass})
MERGE (tc)-[:HAS_RISK]->(risk)
RETURN count(risk) AS risks;

// One member with their active conditions and medications. Replaces the member's condition and
// medication links, so re-seeding after a data edit doesn't leave stale edges.
// Params: $member = {id, name, age, sex, memberSince}, $conditions = [{code, display, onset}],
//         $medications = [{name, class, dose, route, frequency, start}]
// @name seed-member
MERGE (m:Member {id: $member.id})
SET m.name = $member.name, m.age = $member.age, m.sex = $member.sex, m.memberSince = $member.memberSince,
    m.plan = 'All-Inclusive', m.synthetic = true
WITH m
OPTIONAL MATCH (m)-[oldRel:HAS_CONDITION|TAKES]->()
DELETE oldRel
WITH DISTINCT m
FOREACH (c IN $conditions |
  MERGE (cn:Condition {code: c.code})
  SET cn.display = c.display
  MERGE (m)-[hc:HAS_CONDITION]->(cn)
  SET hc.onset = c.onset)
FOREACH (md IN $medications |
  MERGE (med:Medication {name: md.name})
  MERGE (tc:TherapyClass {name: md.class})
  MERGE (med)-[:IN_CLASS]->(tc)
  MERGE (m)-[t:TAKES]->(med)
  SET t.dose = md.dose, t.route = md.route, t.frequency = md.frequency, t.start = md.start)
RETURN m.id AS memberId;
