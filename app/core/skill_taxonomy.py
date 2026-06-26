"""
Skill Taxonomy - 80+ Skills Organized by Category - Phase 2.

ponytail: Flat list with category tags. Skills are canonical names
(case-insensitive matching done at extraction time).
Covers Peru/Latam tech market with modern tooling.
"""

from typing import NamedTuple


class Skill(NamedTuple):
    """A canonical skill with its categories and aliases."""

    name: str  # Canonical display name
    category: str  # Primary category
    aliases: list[str]  # Alternative names for matching
    is_premium: bool  # AI-required for extraction (vs regex-only)


# ─────────────────────────────────────────────────────────────────────────────
# PROGRAMMING LANGUAGES
# ─────────────────────────────────────────────────────────────────────────────
LANGUAGES = [
    Skill(
        "Python", "language", ["python", "python3", "django", "flask", "fastapi"], False
    ),
    Skill("Java", "language", ["java", "java8", "java11", "java17", "spring"], False),
    Skill("JavaScript", "language", ["javascript", "js", "ecmascript"], False),
    Skill("TypeScript", "language", ["typescript", "ts"], False),
    Skill("C#", "language", ["c#", "csharp", ".net", "dotnet", "asp.net"], False),
    Skill("PHP", "language", ["php", "laravel", "symfony"], False),
    Skill("Go", "language", ["go", "golang"], False),
    Skill("Rust", "language", ["rust", "rustlang"], False),
    Skill("Swift", "language", ["swift", "swiftui"], False),
    Skill("Kotlin", "language", ["kotlin", "android"], False),
    Skill("Scala", "language", ["scala"], False),
    Skill("Ruby", "language", ["ruby", "rails", "ruby on rails"], False),
    Skill("R", "language", ["r", "r programming", "rstudio"], False),
    Skill("SQL", "language", ["sql", "mysql", "postgresql", "plsql", "tsql"], False),
    Skill("HTML/CSS", "language", ["html", "css", "scss", "sass", "less"], False),
    Skill(
        "Bash/Shell", "language", ["bash", "shell", "sh", "zsh", "powershell"], False
    ),
]

# ─────────────────────────────────────────────────────────────────────────────
# FRAMEWORKS & LIBRARIES
# ─────────────────────────────────────────────────────────────────────────────
FRAMEWORKS = [
    Skill(
        "React",
        "framework",
        ["react", "reactjs", "react.js", "nextjs", "next.js"],
        False,
    ),
    Skill("Angular", "framework", ["angular", "angularjs", "angular.js"], False),
    Skill("Vue.js", "framework", ["vue", "vuejs", "vue.js", "nuxt", "nuxtjs"], False),
    Skill(
        "Node.js",
        "framework",
        ["node", "nodejs", "node.js", "express", "expressjs"],
        False,
    ),
    Skill("NestJS", "framework", ["nestjs", "nest.js"], False),
    Skill("Spring Boot", "framework", ["spring boot", "springboot"], False),
    Skill("Flutter", "framework", ["flutter"], False),
    Skill("React Native", "framework", ["react native"], False),
    Skill("Next.js", "framework", ["nextjs", "next.js"], False),
    Skill("FastAPI", "framework", ["fastapi"], False),
    Skill("Django", "framework", ["django"], False),
    Skill("Laravel", "framework", ["laravel"], False),
    Skill("Svelte", "framework", ["svelte", "sveltekit"], False),
    Skill("jQuery", "framework", ["jquery"], False),
    Skill("Bootstrap", "framework", ["bootstrap", "tailwindcss", "tailwind"], False),
    Skill("Tailwind CSS", "framework", ["tailwind", "tailwindcss"], False),
    Skill("Redux", "framework", ["redux", "redux toolkit"], False),
    Skill("GraphQL", "framework", ["graphql", "apollo"], False),
    Skill("REST API", "framework", ["rest", "restful", "rest api", "api rest"], False),
]

# ─────────────────────────────────────────────────────────────────────────────
# CLOUD & DEVOPS
# ─────────────────────────────────────────────────────────────────────────────
CLOUD_DEVOPS = [
    Skill("AWS", "cloud", ["aws", "amazon web services", "ec2", "s3", "lambda"], False),
    Skill("Azure", "cloud", ["azure", "microsoft azure", "az"], False),
    Skill(
        "Google Cloud", "cloud", ["gcp", "google cloud", "google cloud platform"], False
    ),
    Skill("Docker", "devops", ["docker", "dockerfile", "docker compose"], False),
    Skill("Kubernetes", "devops", ["kubernetes", "k8s", "k8"], False),
    Skill("Terraform", "devops", ["terraform", "tf", "iac"], False),
    Skill("Ansible", "devops", ["ansible", "ansible playbooks"], False),
    Skill("Jenkins", "devops", ["jenkins", "jenkins ci"], False),
    Skill("GitHub Actions", "devops", ["github actions", "gh actions", "ci/cd"], False),
    Skill("GitLab CI", "devops", ["gitlab ci", "gitlab-ci", "gitci"], False),
    Skill("Prometheus", "devops", ["prometheus", "prom"], False),
    Skill("Grafana", "devops", ["grafana"], False),
    Skill("ELK Stack", "devops", ["elk", "elasticsearch", "logstash", "kibana"], False),
    Skill("Linux", "devops", ["linux", "ubuntu", "centos", "debian", "redhat"], False),
    Skill("Nginx", "devops", ["nginx"], False),
    Skill("Apache", "devops", ["apache", "httpd"], False),
    Skill("Vault", "devops", ["vault", "hashicorp vault"], False),
    Skill("Helm", "devops", ["helm", "helm charts"], False),
]

# ─────────────────────────────────────────────────────────────────────────────
# DATA & AI
# ─────────────────────────────────────────────────────────────────────────────
DATA_AI = [
    Skill("Machine Learning", "data", ["machine learning", "ml", "ml engineer"], True),
    Skill("Deep Learning", "data", ["deep learning", "dl", "neural networks"], True),
    Skill("TensorFlow", "data", ["tensorflow", "tf"], False),
    Skill("PyTorch", "data", ["pytorch", "torch"], False),
    Skill("Pandas", "data", ["pandas", "python pandas"], False),
    Skill("NumPy", "data", ["numpy", "numpy arrays"], False),
    Skill("Scikit-learn", "data", ["scikit-learn", "sklearn"], False),
    Skill(
        "NLP", "data", ["nlp", "natural language processing", "text analytics"], True
    ),
    Skill(
        "Computer Vision", "data", ["computer vision", "cv", "image processing"], True
    ),
    Skill(
        "AI Generativa",
        "data",
        ["generative ai", "genai", "llm", "openai", "gpt", "rag"],
        True,
    ),
    Skill("Hugging Face", "data", ["hugging face", "transformers", "hf"], True),
    Skill("LangChain", "data", ["langchain", "llm frameworks"], True),
    Skill("Spark", "data", ["spark", "pyspark", "apache spark"], False),
    Skill("Airflow", "data", ["airflow", "apache airflow"], False),
    Skill("Kafka", "data", ["kafka", "apache kafka", "confluent"], False),
    Skill("dbt", "data", ["dbt", "data build tool"], False),
    Skill("Snowflake", "data", ["snowflake"], False),
    Skill("BigQuery", "data", ["bigquery", "google bigquery"], False),
    Skill("Databricks", "data", ["databricks", "dbricks"], False),
    Skill("ETL", "data", ["etl", "extract transform load"], False),
    Skill("Data Warehouse", "data", ["data warehouse", "warehouse"], False),
]

# ─────────────────────────────────────────────────────────────────────────────
# DATABASES
# ─────────────────────────────────────────────────────────────────────────────
DATABASES = [
    Skill("PostgreSQL", "database", ["postgresql", "postgres", "psql"], False),
    Skill("MySQL", "database", ["mysql", "mariadb"], False),
    Skill("MongoDB", "database", ["mongodb", "mongo"], False),
    Skill("Redis", "database", ["redis"], False),
    Skill("Oracle", "database", ["oracle", "oracle db", "oracle database"], False),
    Skill(
        "SQL Server", "database", ["sql server", "mssql", "microsoft sql server"], False
    ),
    Skill("SQLite", "database", ["sqlite"], False),
    Skill("DynamoDB", "database", ["dynamodb", "amazon dynamodb", "dynamo"], False),
    Skill("Cassandra", "database", ["cassandra", "apache cassandra"], False),
    Skill("Neo4j", "database", ["neo4j", "graph database"], False),
    Skill("Elasticsearch", "database", ["elasticsearch", "elastic"], False),
]

# ─────────────────────────────────────────────────────────────────────────────
# BUSINESS INTELLIGENCE & VISUALIZATION
# ─────────────────────────────────────────────────────────────────────────────
BI_VIZ = [
    Skill("Power BI", "bi", ["power bi", "powerbi", "power_bi", "pbi"], False),
    Skill("Tableau", "bi", ["tableau"], False),
    Skill("Looker", "bi", ["looker", "google looker"], False),
    Skill("Qlik", "bi", ["qlik", "qlikview", "qliksense"], False),
    Skill("Excel", "bi", ["excel", "microsoft excel", "vba", "macros"], False),
    Skill(
        "Google Data Studio",
        "bi",
        ["data studio", "google data studio", "looker studio"],
        False,
    ),
    Skill("Metabase", "bi", ["metabase"], False),
    Skill("D3.js", "bi", ["d3", "d3.js", "data visualization"], False),
]

# ─────────────────────────────────────────────────────────────────────────────
# PROJECT MANAGEMENT & SOFT SKILLS
# ─────────────────────────────────────────────────────────────────────────────
PM_SOFT = [
    Skill("Agile", "management", ["agile", "agile methodology", "agile scrum"], False),
    Skill("Scrum", "management", ["scrum", "scrum master"], False),
    Skill("Kanban", "management", ["kanban"], False),
    Skill("Jira", "management", ["jira", "atlassian"], False),
    Skill("Confluence", "management", ["confluence"], False),
    Skill("Trello", "management", ["trello"], False),
    Skill("Asana", "management", ["asana"], False),
    Skill("Monday.com", "management", ["monday", "monday.com"], False),
    Skill(
        "Product Management",
        "management",
        ["product manager", "product owner", "product management"],
        False,
    ),
    Skill(
        "Stakeholder Management",
        "management",
        ["stakeholder", "stakeholder management"],
        False,
    ),
    Skill(
        "Technical Writing",
        "soft",
        ["technical writing", "documentation", "docs"],
        False,
    ),
    Skill("Communication", "soft", ["communication", "comunicación"], False),
    Skill(
        "Problem Solving",
        "soft",
        ["problem solving", "problem-solving", "troubleshooting"],
        False,
    ),
    Skill("Team Leadership", "soft", ["leadership", "team lead", "tech lead"], False),
]

# ─────────────────────────────────────────────────────────────────────────────
# SECURITY
# ─────────────────────────────────────────────────────────────────────────────
SECURITY = [
    Skill(
        "Cybersecurity",
        "security",
        ["cybersecurity", "infosec", "information security"],
        False,
    ),
    Skill(
        "Ethical Hacking",
        "security",
        ["ethical hacking", "penetration testing", "pentest"],
        True,
    ),
    Skill("SIEM", "security", ["siem", "splunk", "arcsight"], False),
    Skill(
        "Network Security", "security", ["network security", "firewall", "vpn"], False
    ),
    Skill(
        "IAM", "security", ["iam", "identity access management", "oauth", "saml"], False
    ),
    Skill("Cloud Security", "security", ["cloud security", "cloudsec"], True),
    Skill("DevSecOps", "security", ["devsecops", "security automation"], False),
]

# ─────────────────────────────────────────────────────────────────────────────
# MOBILE
# ─────────────────────────────────────────────────────────────────────────────
MOBILE = [
    Skill("iOS Development", "mobile", ["ios", "swift", "objective-c", "xcode"], False),
    Skill(
        "Android Development", "mobile", ["android", "kotlin", "java android"], False
    ),
    Skill("React Native", "mobile", ["react native", "rn"], False),
    Skill("Flutter", "mobile", ["flutter", "dart"], False),
    Skill("Xamarin", "mobile", ["xamarin", "c# mobile"], False),
]

# ─────────────────────────────────────────────────────────────────────────────
# QA & TESTING
# ─────────────────────────────────────────────────────────────────────────────
QA_TESTING = [
    Skill("Selenium", "qa", ["selenium", "selenium webdriver"], False),
    Skill("Cypress", "qa", ["cypress", "cypress.io"], False),
    Skill("Playwright", "qa", ["playwright", "playwright test"], False),
    Skill("Jest", "qa", ["jest", "jestjs"], False),
    Skill("Mocha", "qa", ["mocha", "mochajs"], False),
    Skill("JUnit", "qa", ["junit", "junit5", "java testing"], False),
    Skill("PyTest", "qa", ["pytest", "python testing", "unittest"], False),
    Skill("Postman", "qa", ["postman", "api testing"], False),
    Skill("SoapUI", "qa", ["soapui"], False),
    Skill("Load Testing", "qa", ["load testing", "jmeter", "k6", "gatling"], False),
    Skill("Manual Testing", "qa", ["manual testing", "tester"], False),
    Skill("Automated Testing", "qa", ["test automation", "automation testing"], False),
]

# ─────────────────────────────────────────────────────────────────────────────
# DEVOPS & INFRASTRUCTURE (expanded)
# ─────────────────────────────────────────────────────────────────────────────
INFRA = [
    Skill("Git", "infra", ["git", "github", "gitlab", "bitbucket"], False),
    Skill("CI/CD", "infra", ["ci/cd", "cicd", "continuous integration"], False),
    Skill("CloudFormation", "infra", ["cloudformation", "aws cfn"], False),
    Skill("Pulumi", "infra", ["pulumi", "infrastructure as code"], False),
    Skill(
        "Serverless",
        "infra",
        ["serverless", "lambda", "azure functions", "cloud functions"],
        False,
    ),
    Skill(
        "Microservices",
        "infra",
        ["microservices", "microservices architecture", "service mesh"],
        True,
    ),
    Skill("Docker Swarm", "infra", ["docker swarm", "swarm"], False),
    Skill("OpenShift", "infra", ["openshift", "ocp"], False),
    Skill("Terraform Cloud", "infra", ["terraform cloud", "tfcloud"], False),
    Skill("ServiceNow", "infra", ["servicenow", "itil"], False),
]

# ─────────────────────────────────────────────────────────────────────────────
# SOFT SKILLS / DOMAIN KNOWLEDGE
# ─────────────────────────────────────────────────────────────────────────────
DOMAIN = [
    Skill("SAP", "domain", ["sap", "sap erp", "sap fico", "sap abap"], False),
    Skill("Salesforce", "domain", ["salesforce", "crm", "sfdc"], False),
    Skill("Fintech", "domain", ["fintech", "financial technology", "banking"], True),
    Skill(
        "E-commerce", "domain", ["e-commerce", "ecommerce", "shopify", "magento"], False
    ),
    Skill("Healthtech", "domain", ["healthtech", "health tech", "hipaa"], True),
    Skill("Edtech", "domain", ["edtech", "education technology", "elearning"], True),
    Skill(
        "Blockchain",
        "domain",
        ["blockchain", "web3", "crypto", "solidity", "nft"],
        True,
    ),
    Skill("IoT", "domain", ["iot", "internet of things", "embedded"], False),
    Skill("CRM", "domain", ["crm", "customer relationship", "dynamics"], False),
    Skill("ERP", "domain", ["erp", "enterprise resource planning"], False),
    Skill(
        "UX Research", "domain", ["ux research", "user research", "usability"], False
    ),
    Skill("SEO/SEM", "domain", ["seo", "sem", "search engine"], False),
    Skill("Growth Hacking", "domain", ["growth hacking", "growth"], False),
]

# ─────────────────────────────────────────────────────────────────────────────
# CONSOLIDATE ALL SKILLS
# ─────────────────────────────────────────────────────────────────────────────
ALL_SKILLS: list[Skill] = (
    LANGUAGES
    + FRAMEWORKS
    + CLOUD_DEVOPS
    + DATA_AI
    + DATABASES
    + BI_VIZ
    + PM_SOFT
    + SECURITY
    + MOBILE
    + QA_TESTING
    + INFRA
    + DOMAIN
)

# Fast lookup: canonical name -> Skill
SKILL_BY_NAME: dict[str, Skill] = {s.name: s for s in ALL_SKILLS}

# Fast lookup: alias (lowercase) -> canonical name
ALIAS_TO_SKILL: dict[str, str] = {}
for skill in ALL_SKILLS:
    ALIAS_TO_SKILL[skill.name.lower()] = skill.name
    for alias in skill.aliases:
        ALIAS_TO_SKILL[alias.lower()] = skill.name

# All canonical skill names as a flat list
ALL_SKILL_NAMES: list[str] = [s.name for s in ALL_SKILLS]

# Skills that require AI extraction (premium/ambiguous)
PREMIUM_SKILLS: list[str] = [s.name for s in ALL_SKILLS if s.is_premium]

# Skills by category
SKILLS_BY_CATEGORY: dict[str, list[Skill]] = {}
for skill in ALL_SKILLS:
    if skill.category not in SKILLS_BY_CATEGORY:
        SKILLS_BY_CATEGORY[skill.category] = []
    SKILLS_BY_CATEGORY[skill.category].append(skill)

# Category display names
CATEGORY_DISPLAY: dict[str, str] = {
    "language": "Lenguajes de Programación",
    "framework": "Frameworks y Librerías",
    "cloud": "Cloud",
    "devops": "DevOps",
    "data": "Datos e IA",
    "database": "Bases de Datos",
    "bi": "Business Intelligence",
    "management": "Gestión de Proyectos",
    "soft": "Habilidades Blandas",
    "security": "Seguridad",
    "mobile": "Desarrollo Mobile",
    "qa": "QA y Testing",
    "infra": "Infraestructura",
    "domain": "Dominio de Negocio",
}


__all__ = [
    "Skill",
    "ALL_SKILLS",
    "ALL_SKILL_NAMES",
    "PREMIUM_SKILLS",
    "SKILL_BY_NAME",
    "ALIAS_TO_SKILL",
    "SKILLS_BY_CATEGORY",
    "CATEGORY_DISPLAY",
    "LANGUAGES",
    "FRAMEWORKS",
    "CLOUD_DEVOPS",
    "DATA_AI",
    "DATABASES",
    "BI_VIZ",
    "PM_SOFT",
    "SECURITY",
    "MOBILE",
    "QA_TESTING",
    "INFRA",
    "DOMAIN",
]
