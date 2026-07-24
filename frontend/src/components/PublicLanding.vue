<script setup>
import {
  ArrowRight,
  BarChart3,
  BookOpenCheck,
  CheckCircle2,
  GraduationCap,
  ShieldCheck,
  Sparkles,
  UploadCloud,
} from "lucide-vue-next";

const emit = defineEmits(["login"]);

const steps = [
  {
    title: "Importation des ressources",
    description: "L'enseignant ajoute les supports pédagogiques de son cours.",
    icon: UploadCloud,
  },
  {
    title: "Création de l'examen",
    description: "La plateforme prépare un examen adapté aux paramètres choisis.",
    icon: Sparkles,
  },
  {
    title: "Révision et validation",
    description: "L'enseignant vérifie, ajuste et valide chaque question.",
    icon: CheckCircle2,
  },
  {
    title: "Publication",
    description: "L'examen validé devient disponible dans l'espace étudiant.",
    icon: BookOpenCheck,
  },
  {
    title: "Passage et résultats",
    description: "Les étudiants répondent puis consultent leurs résultats détaillés.",
    icon: BarChart3,
  },
];
</script>

<template>
  <main class="landing-page">
    <section class="landing-hero">
      <div class="hero-shade" aria-hidden="true"></div>

      <header class="landing-nav">
        <a class="landing-brand" href="#accueil" aria-label="EvalGuard AI - Accueil">
          <span class="brand-mark"><GraduationCap :size="23" /></span>
          <span>EvalGuard AI</span>
        </a>

        <nav aria-label="Navigation principale">
          <a href="#espaces">Espaces</a>
          <a href="#fonctionnement">Fonctionnement</a>
          <button type="button" class="nav-login" @click="emit('login')">
            Se connecter
          </button>
        </nav>
      </header>

      <div id="accueil" class="hero-content">
        <span class="hero-badge"><Sparkles :size="15" /> Évaluation augmentée par l'IA</span>
        <h1>EvalGuard AI</h1>
        <p class="hero-title">La plateforme intelligente d'évaluation académique</p>
        <p class="hero-description">
          Concevez, validez et diffusez des examens fiables à partir de vos ressources
          pédagogiques, dans un espace sécurisé pour chaque rôle.
        </p>
        <div class="hero-actions">
          <button type="button" class="landing-button primary" @click="emit('login')">
            <span>Accéder à mon espace</span>
            <ArrowRight :size="18" />
          </button>
          <a class="landing-button secondary" href="#espaces">Découvrir la plateforme</a>
        </div>
      </div>
    </section>

    <section id="espaces" class="portal-section">
      <div class="landing-container">
        <div class="section-heading">
          <span class="section-kicker">Des espaces adaptés</span>
          <h2>Une plateforme pensée pour l'enseignement supérieur</h2>
          <p>
            Chaque utilisateur retrouve les outils utiles à son travail, de la création de
            l'examen jusqu'à l'analyse de sa qualité.
          </p>
        </div>

        <div class="portal-grid">
          <article class="portal-card teacher-card">
            <span class="portal-icon"><GraduationCap :size="24" /></span>
            <div>
              <h3>Portail Enseignant</h3>
              <p>Créez, révisez, validez et publiez vos examens avant leur diffusion.</p>
            </div>
            <button type="button" @click="emit('login')">
              <span>Se connecter</span>
              <ArrowRight :size="17" />
            </button>
          </article>

          <article class="portal-card student-card">
            <span class="portal-icon"><BookOpenCheck :size="24" /></span>
            <div>
              <h3>Portail Étudiant</h3>
              <p>Passez les examens publiés et consultez vos notes et vos corrections.</p>
            </div>
            <button type="button" @click="emit('login')">
              <span>Se connecter</span>
              <ArrowRight :size="17" />
            </button>
          </article>

          <article class="portal-card technical-card">
            <span class="portal-icon"><ShieldCheck :size="24" /></span>
            <div>
              <h3>Administration</h3>
              <p>Suivez la pédagogie, les utilisateurs et la qualité des agents IA.</p>
            </div>
            <button type="button" @click="emit('login')">
              <span>Se connecter</span>
              <ArrowRight :size="17" />
            </button>
          </article>
        </div>
      </div>
    </section>

    <section id="fonctionnement" class="process-section">
      <div class="landing-container">
        <div class="section-heading compact">
          <span class="section-kicker">Un parcours simple</span>
          <h2>Comment ça fonctionne ?</h2>
        </div>

        <ol class="process-list">
          <li v-for="(step, index) in steps" :key="step.title">
            <span class="step-number">{{ index + 1 }}</span>
            <component :is="step.icon" :size="21" class="step-icon" />
            <div>
              <h3>{{ step.title }}</h3>
              <p>{{ step.description }}</p>
            </div>
          </li>
        </ol>
      </div>
    </section>

    <footer class="landing-footer">
      <div class="landing-container footer-inner">
        <span class="landing-brand footer-brand">
          <span class="brand-mark"><GraduationCap :size="21" /></span>
          <span>EvalGuard AI</span>
        </span>
        <p>Évaluation académique fiable, claire et accessible.</p>
        <button type="button" @click="emit('login')">Accéder au portail</button>
      </div>
    </footer>
  </main>
</template>

<style scoped>
.landing-page {
  min-width: 320px;
  overflow-x: hidden;
  background: #ffffff;
  color: #14213a;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  letter-spacing: 0;
}

.landing-container,
.landing-nav,
.hero-content {
  width: min(1120px, calc(100% - 40px));
  margin-inline: auto;
}

.landing-hero {
  position: relative;
  min-height: 610px;
  isolation: isolate;
  background-image: url("/images/examai-library-hero.png");
  background-position: center;
  background-size: cover;
  color: #ffffff;
}

.hero-shade {
  position: absolute;
  inset: 0;
  z-index: -1;
  background: rgba(5, 18, 38, 0.63);
}

.landing-nav {
  display: flex;
  min-height: 76px;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.18);
}

.landing-brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: inherit;
  font-size: 19px;
  font-weight: 800;
  text-decoration: none;
}

.brand-mark {
  display: inline-grid;
  width: 40px;
  height: 40px;
  place-items: center;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.12);
}

.landing-nav nav {
  display: flex;
  align-items: center;
  gap: 24px;
}

.landing-nav nav a {
  color: #e8eef8;
  font-size: 14px;
  font-weight: 650;
  text-decoration: none;
}

.nav-login,
.landing-button,
.portal-card button,
.landing-footer button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  border-radius: 5px;
  font-weight: 750;
  text-decoration: none;
  transition: transform 160ms ease, background-color 160ms ease, border-color 160ms ease;
}

.nav-login {
  min-height: 40px;
  border: 1px solid rgba(255, 255, 255, 0.42);
  background: rgba(5, 18, 38, 0.36);
  color: #ffffff;
  padding: 0 17px;
}

.hero-content {
  display: grid;
  max-width: 1120px;
  justify-items: start;
  padding-top: 74px;
  padding-bottom: 78px;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border: 1px solid rgba(147, 197, 253, 0.5);
  border-radius: 999px;
  background: rgba(30, 64, 175, 0.28);
  color: #dbeafe;
  padding: 7px 11px;
  font-size: 13px;
  font-weight: 700;
}

.hero-content h1 {
  margin: 22px 0 0;
  font-family: Georgia, "Times New Roman", serif;
  font-size: clamp(48px, 8vw, 82px);
  line-height: 0.95;
  letter-spacing: 0;
}

.hero-title {
  max-width: 690px;
  margin: 16px 0 0;
  color: #ffffff;
  font-family: Georgia, "Times New Roman", serif;
  font-size: clamp(27px, 4vw, 43px);
  font-weight: 700;
  line-height: 1.08;
}

.hero-description {
  max-width: 620px;
  margin: 18px 0 0;
  color: #dbe5f2;
  font-size: 17px;
  line-height: 1.65;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 28px;
}

.landing-button {
  min-height: 48px;
  border: 1px solid transparent;
  padding: 0 20px;
}

.landing-button.primary {
  background: #2f70e8;
  color: #ffffff;
}

.landing-button.secondary {
  border-color: rgba(255, 255, 255, 0.45);
  background: rgba(5, 18, 38, 0.34);
  color: #ffffff;
}

.landing-button:hover,
.nav-login:hover,
.portal-card button:hover,
.landing-footer button:hover {
  transform: translateY(-2px);
}

.portal-section {
  padding: 74px 0 84px;
  background: #ffffff;
}

.section-heading {
  max-width: 790px;
  margin: 0 auto 34px;
  text-align: center;
}

.section-kicker {
  display: block;
  margin-bottom: 10px;
  color: #2563eb;
  font-size: 13px;
  font-weight: 800;
  text-transform: uppercase;
}

.section-heading h2 {
  margin: 0;
  color: #14213a;
  font-family: Georgia, "Times New Roman", serif;
  font-size: clamp(29px, 4vw, 42px);
  line-height: 1.15;
  letter-spacing: 0;
}

.section-heading p {
  margin: 16px auto 0;
  color: #5d6b82;
  font-size: 16px;
  line-height: 1.65;
}

.portal-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.portal-card {
  display: grid;
  min-height: 270px;
  grid-template-rows: auto 1fr auto;
  gap: 20px;
  border-radius: 7px;
  color: #ffffff;
  padding: 24px;
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.15);
}

.teacher-card {
  background: #173f78;
}

.student-card {
  background: #0f766e;
}

.technical-card {
  background: #29374d;
}

.portal-icon {
  display: inline-grid;
  width: 44px;
  height: 44px;
  place-items: center;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.13);
  color: #ffffff;
}

.portal-card h3 {
  margin: 0 0 9px;
  font-size: 20px;
}

.portal-card p {
  margin: 0;
  color: rgba(255, 255, 255, 0.8);
  line-height: 1.55;
}

.portal-card button {
  min-height: 43px;
  border: 1px solid rgba(255, 255, 255, 0.25);
  background: rgba(255, 255, 255, 0.12);
  color: #ffffff;
}

.process-section {
  padding: 76px 0 88px;
  background: #f1f5f9;
}

.section-heading.compact {
  margin-bottom: 42px;
}

.process-list {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0;
  padding: 0;
  margin: 0;
  list-style: none;
}

.process-list li {
  display: grid;
  min-height: 210px;
  align-content: start;
  justify-items: center;
  gap: 12px;
  border-right: 1px solid #cad5e3;
  padding: 0 20px;
  text-align: center;
}

.process-list li:last-child {
  border-right: 0;
}

.step-number {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border-radius: 50%;
  background: #2563eb;
  color: #ffffff;
  font-size: 14px;
  font-weight: 800;
}

.step-icon {
  color: #0f766e;
}

.process-list h3 {
  margin: 0 0 8px;
  color: #14213a;
  font-size: 16px;
}

.process-list p {
  margin: 0;
  color: #64748b;
  font-size: 14px;
  line-height: 1.5;
}

.landing-footer {
  background: #10233f;
  color: #ffffff;
  padding: 28px 0;
}

.footer-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

.footer-inner p {
  margin: 0;
  color: #b9c7d9;
}

.landing-footer button {
  min-height: 41px;
  border: 1px solid #86a7d1;
  background: transparent;
  color: #ffffff;
  padding: 0 16px;
}

@media (max-width: 860px) {
  .landing-nav nav > a {
    display: none;
  }

  .landing-hero {
    min-height: 580px;
    background-position: 62% center;
  }

  .hero-content {
    padding-top: 64px;
  }

  .portal-grid {
    grid-template-columns: 1fr;
  }

  .portal-card {
    min-height: 230px;
  }

  .process-list {
    grid-template-columns: 1fr;
  }

  .process-list li {
    min-height: 0;
    grid-template-columns: 34px 24px minmax(0, 1fr);
    justify-items: start;
    align-items: start;
    border-right: 0;
    border-bottom: 1px solid #cad5e3;
    padding: 20px 0;
    text-align: left;
  }

  .process-list li:last-child {
    border-bottom: 0;
  }

  .footer-inner {
    align-items: flex-start;
    flex-direction: column;
  }
}

@media (max-width: 560px) {
  .landing-container,
  .landing-nav,
  .hero-content {
    width: min(100% - 28px, 1120px);
  }

  .landing-nav {
    min-height: 68px;
  }

  .landing-hero {
    min-height: 560px;
  }

  .hero-content {
    padding-top: 48px;
    padding-bottom: 56px;
  }

  .hero-content h1 {
    font-size: 52px;
  }

  .hero-title {
    font-size: 29px;
  }

  .hero-description {
    font-size: 15px;
    line-height: 1.55;
  }

  .hero-actions,
  .landing-button {
    width: 100%;
  }

  .portal-section,
  .process-section {
    padding: 58px 0 66px;
  }

  .portal-card {
    min-height: 220px;
  }

  .nav-login {
    padding: 0 12px;
  }
}
</style>
