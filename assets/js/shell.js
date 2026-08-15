/* ============================================================
   plana / shell.js — behaviour shared by every page.
   Replaces jQuery + Bootstrap JS + MDBootstrap JS + components.js.
   No dependencies.
   ============================================================ */
(function () {
  'use strict';

  // Site root. Was '/plana' while the rebuild lived in a draft folder.
  var BASE = '';

  /* ------------------------------------------------------------
     Primary navigation — one source, injected into every page, so the
     chrome cannot drift between pages.

     Labels are deliberately durable. Nothing here names an employer, a
     team, or a current specialism: a personal site should outlive any
     one job.
     ------------------------------------------------------------ */
  /* Three items only. Work and Creativity are reached from the footer
     directory, which lists every destination — so dropping them from the top
     bar costs no reachability. */
  var NAV = [
    [BASE + '/blog/', 'Writing', '写作'],
    [BASE + '/publications.html', 'Publications', '出版'],
    [BASE + '/contact.html', 'Contact', '联系', 'cta']
  ];

  /* ------------------------------------------------------------
     Footer directory — every public destination.

     Private material is deliberately absent: notes/papers, notes/LP and
     cv/amzn are personal notes and an internal CV, not publications.
     Offices is likewise omitted here — it is a personal curiosity, not a
     credential, and stays reachable from the sitemap.
     ------------------------------------------------------------ */
  var DIRECTORY = [
    {
      en: 'Tech & Science', zh: '科技',
      links: [
        [BASE + '/work.html', 'Work', '作品'],
        [BASE + '/publications.html', 'Books & papers', '书籍与论文'],
        [BASE + '/invited-talks.html', 'Talks & lectures', '演讲与讲座'],
        [BASE + '/service.html', 'Academic service', '学术服务']
      ]
    },
    {
      en: 'Writing', zh: '写作',
      links: [
        [BASE + '/blog/', 'All writing', '全部文章'],
        ['/feed.xml', 'RSS feed', 'RSS']
      ]
    },
    {
      en: 'Creativity', zh: '创作',
      links: [
        [BASE + '/creativity.html', 'Design & photography', '设计与摄影'],
        [BASE + '/maps.html', 'Maps', '地图']
      ]
    },
    {
      en: 'About', zh: '关于',
      links: [
        [BASE + '/experience.html', 'Experience', '经历'],
        [BASE + '/endorsements.html', 'Endorsements', '行业背书'],
        [BASE + '/news.html', 'News', '动态']
      ]
    },
    {
      // Social links follow one order everywhere on the site:
      // LinkedIn, X, GitHub, Substack, Rednote, Instagram.
      // This group carries the professional three; the rest live on the
      // contact page, which is where someone looking for them goes.
      en: 'Elsewhere', zh: '其他',
      links: [
        ['https://www.linkedin.com/in/pengandy-us', 'LinkedIn', '领英'],
        ['https://x.com/pymhq', 'X', 'X'],
        ['https://substack.com/@pengandy', 'Substack', 'Substack'],
        [BASE + '/sitemap.html', 'Sitemap', '站点地图']
      ]
    }
  ];

  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');
  }

  function bi(en, zh) {
    return (
      '<span class="lang-en">' + esc(en) + '</span>' +
      '<span class="lang-zh" hidden>' + esc(zh) + '</span>'
    );
  }

  function extAttrs(href) {
    return /^https?:/.test(href) ? ' target="_blank" rel="noopener"' : '';
  }

  /* ---------------- nav ---------------- */
  function buildNav() {
    var mount = document.querySelector('[data-shell-nav]');
    if (!mount) return;
    var links = NAV.map(function (n) {
      return (
        '<a href="' + esc(n[0]) + '"' +
        (n[3] ? ' class="' + n[3] + '"' : '') + '>' +
        bi(n[1], n[2]) + '</a>'
      );
    }).join('');

    mount.innerHTML =
      '<div class="nav-in">' +
      '<a class="nav-mark" href="' + BASE + '/">Peng, Andy</a>' +
      '<div class="nav-links">' + links + '</div>' +
      '</div>';

    // mark the current page
    var here = location.pathname.replace(/index\.html$/, '');
    mount.querySelectorAll('.nav-links a').forEach(function (a) {
      var path = (a.getAttribute('href') || '').split(/[?#]/)[0];
      var self = document.body.dataset.navMatch;
      if (path === here || (self && path.indexOf(self) !== -1)) {
        a.setAttribute('aria-current', 'page');
      }
    });
  }

  /* ---------------- footer ---------------- */
  function buildFooter() {
    var mount = document.querySelector('[data-shell-footer]');
    if (!mount) return;

    var cols = DIRECTORY.map(function (g) {
      var items = g.links.map(function (l) {
        return (
          '<li><a href="' + esc(l[0]) + '"' + extAttrs(l[0]) + '>' +
          bi(l[1], l[2]) + '</a></li>'
        );
      }).join('');
      return '<div><h4>' + bi(g.en, g.zh) + '</h4><ul>' + items + '</ul></div>';
    }).join('');

    mount.innerHTML =
      '<div class="shell">' +
      '<div class="dir">' + cols + '</div>' +
      '<div class="foot-bar">' +
      '<span>© ' + new Date().getFullYear() + ' Andy Peng</span>' +
      '<div class="foot-tools">' +
      '<div class="seg" role="group" aria-label="Language">' +
      '<button type="button" data-lang="en">EN</button>' +
      '<button type="button" data-lang="zh">中文</button>' +
      '</div>' +
      '<div class="seg" role="group" aria-label="Appearance">' +
      '<button type="button" data-theme-set="light" title="Light">Light</button>' +
      '<button type="button" data-theme-set="dark" title="Dark">Dark</button>' +
      '</div>' +
      '</div></div></div>';

    // The language buttons are bound once, page-wide, by bindLangButtons():
    // posts carry their own EN/中文 pair above the article and both controls
    // have to drive the same switch.
    mount.querySelectorAll('[data-theme-set]').forEach(function (b) {
      b.addEventListener('click', function () {
        setTheme(b.dataset.themeSet);
      });
    });
  }

  /* ---------------- theme ----------------
     Reuses the site's existing contract: localStorage "theme" plus
     html[data-theme], the same pair assets/js/theme.js uses, so the
     preference carries to pages that still run theme.js. */
  function setTheme(mode) {
    localStorage.setItem('theme', mode);
    applyTheme(mode);
  }

  function applyTheme(mode) {
    document.documentElement.setAttribute('data-theme', mode);
    document.querySelectorAll('[data-theme-set]').forEach(function (b) {
      b.classList.toggle('active', b.dataset.themeSet === mode);
    });
  }

  function currentTheme() {
    var saved = localStorage.getItem('theme');
    if (saved === 'dark' || saved === 'light') return saved;
    return window.matchMedia &&
      window.matchMedia('(prefers-color-scheme: dark)').matches
      ? 'dark'
      : 'light';
  }

  /* ---------------- language ----------------
     Same localStorage key as the live site so the choice carries across.
     ?lang=en|zh overrides it, which also makes Chinese links shareable. */
  window.applyLanguage = function (lang) {
    var zh = lang === 'zh';
    document.querySelectorAll('.lang-en').forEach(function (el) {
      // Keep English visible where no translation exists. The pair has to be a
      // *sibling*, so scope the lookup to direct children: a plain descendant
      // query also matches Chinese text inside a nested .note, which wrongly
      // hid the English title and left the entry with no title at all.
      var p = el.parentElement;
      var hasZh = p && p.querySelector(':scope > .lang-zh');
      show(el, !(zh && !!hasZh));
    });
    document.querySelectorAll('.lang-zh').forEach(function (el) {
      show(el, zh);
    });
    document.querySelectorAll('[data-lang]').forEach(function (b) {
      b.classList.toggle('active', b.dataset.lang === lang);
    });
    document.documentElement.lang = zh ? 'zh-Hans' : 'en';
    // Lets page-local widgets that key off the language — the reading-aid
    // outlines in the long posts — rebuild without knowing about this file.
    document.dispatchEvent(
      new CustomEvent('languagechange', { detail: { lang: lang } })
    );
  };

  /* Visibility is the `hidden` attribute, but an inline `display` beats it:
     posts written before this file owned the toggle set display in their own
     script, which silently pinned the body to one language while the titles
     around it still switched. Clearing the inline value keeps those pages
     switchable whatever they did on load. */
  function show(el, visible) {
    if (el.style && el.style.display) el.style.removeProperty('display');
    el.hidden = !visible;
  }

  window.switchLanguage = function (lang) {
    localStorage.setItem('preferredLanguage', lang);
    window.applyLanguage(lang);
  };

  function currentLang() {
    var forced = new URLSearchParams(location.search).get('lang');
    if (forced === 'zh' || forced === 'en') return forced;
    return localStorage.getItem('preferredLanguage') || 'en';
  }

  /* One delegated handler for every EN/中文 control on the page — the footer
     pair this file injects and the pair each translated post carries above its
     article. Delegation also covers controls added after boot. */
  function bindLangButtons() {
    document.addEventListener('click', function (e) {
      var btn = e.target.closest && e.target.closest('[data-lang]');
      if (!btn) return;
      e.preventDefault();
      window.switchLanguage(btn.dataset.lang);
    });
  }

  /* ---------------- sticky nav ---------------- */
  function stickyNav() {
    var nav = document.querySelector('.nav');
    if (!nav) return;
    var probe = document.createElement('div');
    probe.style.cssText = 'position:absolute;top:0;height:1px;width:1px';
    document.body.prepend(probe);
    if (!('IntersectionObserver' in window)) {
      nav.classList.add('is-stuck');
      return;
    }
    new IntersectionObserver(
      function (e) {
        nav.classList.toggle('is-stuck', !e[0].isIntersecting);
      },
      { rootMargin: '-72px 0px 0px 0px' }
    ).observe(probe);
  }

  /* ---------------- reveal ---------------- */
  function reveal() {
    var targets = document.querySelectorAll('.rise:not(.in)');
    if (!targets.length) return;

    var showAll = function () {
      document.querySelectorAll('.rise:not(.in)').forEach(function (el) {
        el.classList.add('in');
      });
    };

    if (!('IntersectionObserver' in window)) {
      showAll();
      return;
    }

    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) {
            e.target.classList.add('in');
            io.unobserve(e.target);
          }
        });
      },
      { rootMargin: '0px 0px -8% 0px', threshold: 0.02 }
    );

    targets.forEach(function (el) {
      var r = el.getBoundingClientRect();
      if (r.top < window.innerHeight && r.bottom > 0) {
        el.classList.add('in'); // already on screen: no animation
      } else {
        io.observe(el);
      }
    });

    clearTimeout(reveal._t);
    reveal._t = setTimeout(showAll, 2500); // failsafe
  }

  /* ---------------- media protection ----------------
     Same behaviour the previous site had on its photo tiles and reels, now
     applied everywhere. Scoped to media: right-click and drag are blocked on
     images and video, but text selection, copying and link context menus
     elsewhere on the page keep working — a document-wide block would be
     hostile to readers for very little gain.

     This is best-effort and always will be: the file is still reachable from
     the network tab. It stops casual right-click-save and drag-to-desktop. */
  function protectMedia() {
    var isMedia = function (t) {
      return t && (t.tagName === 'IMG' || t.tagName === 'VIDEO' ||
                   t.tagName === 'PICTURE' ||
                   (t.closest && t.closest('.gallery figure, .figure, .portrait')));
    };
    document.addEventListener('contextmenu', function (e) {
      if (isMedia(e.target)) e.preventDefault();
    });
    document.addEventListener('dragstart', function (e) {
      if (isMedia(e.target)) e.preventDefault();
    });
    document.querySelectorAll('img, video').forEach(function (el) {
      el.setAttribute('draggable', 'false');
    });
  }

  /* ---------------- boot ---------------- */
  applyTheme(currentTheme()); // before paint work, to avoid a flash
  document.addEventListener('DOMContentLoaded', function () {
    buildNav();
    buildFooter();
    applyTheme(currentTheme());
    bindLangButtons();
    window.applyLanguage(currentLang());
    stickyNav();
    reveal();
    protectMedia();
  });
})();
