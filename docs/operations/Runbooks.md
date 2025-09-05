---
title: Operations Runbooks
owner: DevOps Team
last_updated: 2025-09-01
status: authoritative
---

# Operations Runbooks

> **Incident response procedures and troubleshooting playbooks for healthcare AI platform**

## Table of Contents

1. [Incident Response Framework](#incident-response-framework)
2. [Service-Specific Runbooks](#service-specific-runbooks)
3. [Database Operations](#database-operations)
4. [HIPAA Compliance Issues](#hipaa-compliance-issues)
5. [Performance Issues](#performance-issues)
6. [Security Incidents](#security-incidents)
7. [Emergency Procedures](#emergency-procedures)

## Incident Response Framework

### Severity Levels

| Severity | Description | Response Time | Escalation |
|----------|-------------|---------------|------------|
| **P0 - Critical** | Service down, PHI breach, patient safety risk | <5 minutes | Immediate management + legal |
| **P1 - High** | Degraded performance, compliance issues | <15 minutes | Management notification |
| **P2 - Medium** | Non-critical feature issues | <1 hour | Team lead notification |
| **P3 - Low** | Minor bugs, enhancement requests | <24 hours | Standard workflow |

### Incident Response Team

**On-Call Rotation**:
- **Primary**: DevOps Engineer (24/7)
- **Secondary**: Platform Engineer (business hours)
- **Escalation**: Engineering Manager → CTO → CISO

**Communication Channels**:
- **Immediate**: PagerDuty alerts + SMS
- **Updates**: Slack #incidents channel
- **Stakeholders**: Email updates every 30 minutes for P0/P1

## Service-Specific Runbooks

### API Gateway Issues

**Symptom**: High response times (>100ms for API Gateway)
```bash
# Diagnosis (check all 20 services)
kubectl top pods -l app=api-gateway
kubectl logs -l app=api-gateway --tail=100

# Check all downstream services health
make health  # Checks all 20 services
curl http://auth-rbac:8080/health
curl http://ai-gateway:8000/health
curl http://chat-history:8002/health
curl http://audit-logging:8084/health

# Resolution
# 1. Scale API Gateway if CPU/memory high
kubectl scale deployment api-gateway --replicas=7

# 2. Check confidence-based routing performance
curl http://ai-gateway:8000/metrics | grep confidence_optimization

# 3. Validate cache performance (L1/L2/L3 tiers)
curl http://ai-gateway:8000/cache/stats
```

**Symptom**: Authentication failures
```bash
# Diagnosis
kubectl logs -l app=auth-rbac --tail=100 | grep -i error
curl -v http://auth-rbac:8080/health

# Resolution
# 1. Check JWT secret availability
kubectl get secret auth-secrets -o yaml

# 2. Verify database connectivity
kubectl exec -it auth-pod -- nc -zv postgres 5432

# 3. Restart auth service if needed
kubectl rollout restart deployment/auth-rbac
```

### AI Service Issues

**Symptom**: AI Gateway timeouts (>2000ms)
```bash
# Diagnosis (6 AI services total)
kubectl logs -l app=ai-gateway --tail=100
curl -w "@curl-format.txt" http://ai-gateway:8000/health

# Check GPU resource availability for host services
kubectl describe node -l node-type=gpu
nvidia-smi  # If NVIDIA GPU available

# Resolution
# 1. Check AI service model status
curl http://ai-gateway:8000/health
curl http://embedding-service:8005/health
curl http://generation-service:8006/health

# 2. Scale AI services if needed
kubectl scale deployment ai-gateway --replicas=4
kubectl scale deployment embedding-service --replicas=3
kubectl scale deployment generation-service --replicas=3

# 3. Check GPU host services (BGE + Qwen)
curl http://bge-host:8008/health
curl http://qwen-host:8009/health

# 4. Verify confidence-based optimization
curl http://ai-gateway:8000/cache/confidence-stats
```

**Symptom**: RAG pipeline failures or zero retrieval
```bash
# Diagnosis (intelligent data router + therapeutic cache)
curl http://search-service:8001/health
curl http://embedding-service:8005/health
curl http://ai-gateway:8000/health

# Check vector database connectivity and seeding
kubectl exec -it mongodb-pod -- mongosh --eval "db.therapeutic_content.countDocuments()"
kubectl exec -it postgres-pod -- psql -c "SELECT COUNT(*) FROM chatbot_knowledge.documents;"

# Check confidence-based routing performance
curl http://ai-gateway:8000/router/confidence-stats

# Resolution
# 1. Verify healthcare knowledge base seeding
make seed  # Seeds therapeutic content
python ai_services/ingestion_pipeline/therapeutic_mongodb_seeder.py

# 2. Test intelligent data router
curl http://ai-gateway:8000/search -X POST -d '{"query": "diabetes medication", "route": "auto"}'

# 3. Check therapeutic cache manager
curl http://ai-gateway:8000/cache/therapeutic-stats

# 4. Restart RAG pipeline services
kubectl rollout restart deployment/search-service
kubectl rollout restart deployment/ai-gateway
kubectl rollout restart deployment/embedding-service
```

## Database Operations

### PostgreSQL Issues

**Symptom**: Database connection pool exhaustion
```bash
# Diagnosis
kubectl exec -it postgres-0 -- psql -c "SELECT count(*) FROM pg_stat_activity;"
kubectl logs postgres-0 | grep -i "remaining connection slots"

# Resolution
# 1. Check application connection pool settings
kubectl get configmap database-config -o yaml

# 2. Scale database connections
kubectl patch configmap database-config --patch '{"data":{"max_connections":"200"}}'

# 3. Restart affected services
kubectl rollout restart deployment/auth-rbac
kubectl rollout restart deployment/ai-gateway
```

**Symptom**: Slow query performance
```bash
# Diagnosis
kubectl exec -it postgres-0 -- psql -c "
  SELECT query, calls, total_time, mean_time 
  FROM pg_stat_statements 
  ORDER BY mean_time DESC LIMIT 10;"

# Resolution
# 1. Check for missing indexes
kubectl exec -it postgres-0 -- psql -c "
  SELECT schemaname, tablename, attname, n_distinct, correlation 
  FROM pg_stats 
  WHERE schemaname = 'public';"

# 2. Run ANALYZE on affected tables
kubectl exec -it postgres-0 -- psql -c "ANALYZE;"
```

### MongoDB Issues

**Symptom**: Vector search performance degradation
```bash
# Diagnosis
kubectl exec -it mongodb-0 -- mongo --eval "
  db.therapeutic_content.find().limit(1).explain('executionStats')"

# Check index status
kubectl exec -it mongodb-0 -- mongo --eval "db.therapeutic_content.getIndexes()"

# Resolution
# 1. Rebuild vector indexes
make rebuild-vector-indexes

# 2. Check shard distribution
kubectl exec -it mongodb-0 -- mongo --eval "sh.status()"
```

## HIPAA Compliance Issues

### Audit Log Failures

**Symptom**: Missing audit events
```bash
# Diagnosis
curl http://audit-logging:8084/health
kubectl logs -l app=audit-logging | grep -i error

# Check audit queue status
kubectl exec -it redis-0 -- redis-cli llen audit_events_queue

# Resolution
# 1. Verify audit service health
kubectl describe pod -l app=audit-logging

# 2. Check database connectivity
kubectl exec -it audit-pod -- nc -zv postgres 5432

# 3. Process queued audit events
curl -X POST http://audit-logging:8084/admin/process-queue
```

### PHI Access Violations

**Symptom**: Unauthorized PHI access detected
```bash
# Immediate Response
# 1. Alert security team
curl -X POST http://notification-service:8080/security-alert \
  -d '{"severity": "critical", "type": "phi_access_violation"}'

# 2. Review access logs
kubectl exec -it postgres-0 -- psql -c "
  SELECT * FROM audit_logs 
  WHERE event_type = 'phi_access' 
  AND timestamp > NOW() - INTERVAL '1 hour'
  ORDER BY timestamp DESC;"

# 3. Disable user if needed
curl -X POST http://auth-rbac:8080/admin/disable-user \
  -d '{"user_id": "<user_id>", "reason": "security_investigation"}'
```

## Performance Issues

### High Response Times

**Diagnosis Checklist**:
```bash
# 1. Check service health
make health-check-all

# 2. Monitor key metrics
curl http://api-gateway:8090/metrics | grep response_time
curl http://ai-gateway:8000/metrics | grep duration

# 3. Check database performance
kubectl exec -it postgres-0 -- psql -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"

# 4. Monitor cache hit rates
kubectl exec -it redis-0 -- redis-cli info stats | grep cache_hit_ratio
```

**Resolution Steps**:
1. **Scale services** if CPU/memory high
2. **Optimize queries** if database bottleneck
3. **Increase cache TTL** if cache miss rate high
4. **Enable query caching** for repeated patterns

### Memory Leaks

**Symptom**: Gradually increasing memory usage
```bash
# Diagnosis
kubectl top pods --sort-by=memory
kubectl exec -it <pod-name> -- cat /proc/meminfo

# Monitor memory growth
watch "kubectl top pod <pod-name>"

# Resolution
# 1. Restart affected service
kubectl rollout restart deployment/<service-name>

# 2. Check for memory leak patterns
kubectl logs <pod-name> | grep -i "memory\|oom"

# 3. Scale up if needed as temporary fix
kubectl scale deployment <service-name> --replicas=<new-count>
```

## Security Incidents

### Suspected PHI Breach

**Immediate Response (within 5 minutes)**:
```bash
# 1. Isolate affected systems
kubectl label node <affected-node> security=quarantine
kubectl cordon <affected-node>

# 2. Collect forensic evidence
kubectl logs -l app=<affected-service> > incident-logs-$(date +%s).log
kubectl exec -it postgres-0 -- pg_dump -t audit_logs > audit-snapshot-$(date +%s).sql

# 3. Notify legal team
curl -X POST http://notification-service:8080/legal-alert \
  -d '{"severity": "critical", "type": "potential_phi_breach", "incident_id": "<incident_id>"}'
```

**Investigation Procedures**:
1. **Timeline reconstruction** from audit logs
2. **Scope assessment** of potentially accessed PHI
3. **Impact analysis** for affected patients
4. **Regulatory notification** (if confirmed breach)

### Security Alert Response

**Unusual Access Patterns**:
```bash
# Check for suspicious activity
kubectl exec -it postgres-0 -- psql -c "
  SELECT user_id, COUNT(*), array_agg(DISTINCT event_type)
  FROM audit_logs 
  WHERE timestamp > NOW() - INTERVAL '1 hour'
  GROUP BY user_id
  HAVING COUNT(*) > 100
  ORDER BY count DESC;"

# Block suspicious users temporarily
curl -X POST http://auth-rbac:8080/admin/temporary-suspend \
  -d '{"user_id": "<user_id>", "duration_minutes": 60, "reason": "security_investigation"}'
```

## Emergency Procedures

### Complete System Outage

**Emergency Response Team Assembly**:
1. **DevOps Lead** (primary responder)
2. **Platform Engineer** (technical lead)  
3. **Security Engineer** (if security-related)
4. **Clinical Director** (for patient safety assessment)
5. **AI Engineer** (for AI service issues)

**Recovery Steps for 20-Service Architecture**:
```bash
# 1. Assess scope of outage (20 services total)
kubectl get nodes
kubectl get pods --all-namespaces | grep -v Running
make health  # Check all services

# 2. Check infrastructure status (Terraform-managed)
cd terraform && terraform show | grep "status"
kubectl cluster-info

# 3. Priority service restoration order
# a) Database layer first (4 databases)
kubectl scale statefulset postgres --replicas=3
kubectl scale deployment mongodb --replicas=3
kubectl scale deployment redis --replicas=3
kubectl scale statefulset scylladb --replicas=3

# b) Critical Go microservices (HIPAA compliance)
kubectl scale deployment auth-rbac --replicas=3
kubectl scale deployment audit-logging --replicas=3
kubectl scale deployment content-safety --replicas=2
kubectl scale deployment emergency-access --replicas=2

# c) API Gateway (primary entry point)
kubectl scale deployment api-gateway --replicas=5

# d) Core microservices
kubectl scale deployment chat-history --replicas=3
kubectl scale deployment search-service --replicas=3
kubectl scale deployment billing --replicas=2
kubectl scale deployment consent --replicas=2
kubectl scale deployment background-tasks --replicas=2
kubectl scale deployment relationship-mgmt --replicas=2
kubectl scale deployment user-subscription --replicas=2

# e) Python AI services (6 services + 2 GPU hosts)
kubectl scale deployment ai-gateway --replicas=3
kubectl scale deployment embedding-service --replicas=2
kubectl scale deployment generation-service --replicas=2
kubectl scale deployment bge-host --replicas=2
kubectl scale deployment qwen-host --replicas=2
```

### Data Recovery Procedures

**Backup Restoration**:
```bash
# 1. Identify backup timestamps
kubectl exec -it backup-pod -- ls -la /backups/

# 2. Restore PostgreSQL from backup
kubectl exec -it postgres-0 -- pg_restore -d therapeutic_ai /backups/postgres-latest.dump

# 3. Restore MongoDB from backup  
kubectl exec -it mongodb-0 -- mongorestore /backups/mongodb-latest/

# 4. Verify data integrity
make test-data-integrity

# 5. Resume normal operations
kubectl scale deployment api-gateway --replicas=5
```

### Crisis Communication

**Internal Communication Template**:
```
INCIDENT ALERT - P0 CRITICAL

Service: MultiDB Therapeutic AI Platform
Impact: [Service Down/Degraded/PHI Concern]
Start Time: 2025-09-01 12:00 UTC
Estimated Resolution: TBD

Current Status:
- [Brief description of issue]
- [Actions taken so far]
- [Next steps]

Response Team:
- Incident Commander: [Name]
- Technical Lead: [Name]
- Communications: [Name]

Updates: Every 15 minutes until resolved
```

**External Communication** (if patient-facing impact):
```
We are currently experiencing technical difficulties with our therapeutic AI platform. 
Patient data remains secure and no PHI has been compromised. 
Emergency support remains available at [emergency contact].
Estimated resolution: [timeframe]
```

---

**Runbook Version**: 2.0  
**Last Tested**: 2025-09-01  
**Next Drill**: 2025-10-01  
**Maintained By**: DevOps Team + Security Team