/* =============================================================================
   PDSC — Plateforme de Digitalisation des Services Communaux
   Script unique : mode sombre, menu mobile, sidebar, validation de formulaires,
   previsualisation d'images, upload par glisser-deposer, notifications (AJAX),
   confirmation de suppression, visionneuse PDF, animations et compteurs.
============================================================================= */
(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        initDarkMode();
        initBackToTop();
        initSidebarToggle();
        initTabHashActivation();
        initStatCounters();
        initScrollReveal();
        initPasswordToggles();
        initPasswordStrength();
        initFormValidation();
        initDeleteConfirmations();
        initFileDropZone();
        initAvatarPreview();
        initNotificationMarkRead();
        initPdfViewerControls();
        initAdminEditModals();
        initServiceRequestPrefill();
        initTableSearch();
    });

    /* -----------------------------------------------------------------------
       Recupere le jeton CSRF pour les requetes AJAX (fetch)
    ----------------------------------------------------------------------- */
    function getCsrfToken() {
        var meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }

    /* -----------------------------------------------------------------------
       MODE SOMBRE
    ----------------------------------------------------------------------- */
    function initDarkMode() {
        var root = document.documentElement;
        var toggleBtn = document.getElementById('darkModeToggle');
        var settingsToggle = document.getElementById('darkModeSettingsToggle');
        var stored = localStorage.getItem('pdsc-theme');

        function applyTheme(theme) {
            root.setAttribute('data-bs-theme', theme);
            localStorage.setItem('pdsc-theme', theme);
            if (toggleBtn) {
                var icon = toggleBtn.querySelector('i');
                if (icon) icon.className = theme === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-stars-fill';
            }
            if (settingsToggle) settingsToggle.checked = theme === 'dark';
        }

        var prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
        applyTheme(stored || (prefersDark ? 'dark' : 'light'));

        function toggleTheme() {
            var current = root.getAttribute('data-bs-theme');
            applyTheme(current === 'dark' ? 'light' : 'dark');
        }

        if (toggleBtn) toggleBtn.addEventListener('click', toggleTheme);
        if (settingsToggle) settingsToggle.addEventListener('change', toggleTheme);
    }

    /* -----------------------------------------------------------------------
       BOUTON RETOUR EN HAUT
    ----------------------------------------------------------------------- */
    function initBackToTop() {
        var btn = document.getElementById('backToTop');
        if (!btn) return;
        window.addEventListener('scroll', function () {
            btn.classList.toggle('visible', window.scrollY > 400);
        });
        btn.addEventListener('click', function () {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }

    /* -----------------------------------------------------------------------
       SIDEBAR MOBILE (TABLEAUX DE BORD)
    ----------------------------------------------------------------------- */
    function initSidebarToggle() {
        var toggle = document.getElementById('sidebarToggle');
        var sidebar = document.getElementById('dashboardSidebar');
        if (!toggle || !sidebar) return;

        toggle.addEventListener('click', function () {
            sidebar.classList.toggle('open');
        });

        document.addEventListener('click', function (evt) {
            if (sidebar.classList.contains('open') && !sidebar.contains(evt.target) && evt.target !== toggle && !toggle.contains(evt.target)) {
                sidebar.classList.remove('open');
            }
        });
    }

    /* -----------------------------------------------------------------------
       ACTIVATION D'ONGLET VIA LE HASH DE L'URL (tableau de bord admin)
    ----------------------------------------------------------------------- */
    function initTabHashActivation() {
        var hash = window.location.hash;
        if (!hash) return;
        var trigger = document.querySelector('.admin-tabs [data-bs-target="' + hash + '"]');
        if (trigger && window.bootstrap) {
            var tab = new bootstrap.Tab(trigger);
            tab.show();
            setTimeout(function () {
                trigger.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
            }, 150);
        }
    }

    /* -----------------------------------------------------------------------
       COMPTEURS ANIMES (CHIFFRES CLES DE LA PAGE D'ACCUEIL)
    ----------------------------------------------------------------------- */
    function initStatCounters() {
        var counters = document.querySelectorAll('[data-count]');
        if (!counters.length) return;

        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (!entry.isIntersecting) return;
                animateCounter(entry.target);
                observer.unobserve(entry.target);
            });
        }, { threshold: 0.4 });

        counters.forEach(function (el) { observer.observe(el); });

        function animateCounter(el) {
            var target = parseInt(el.getAttribute('data-count'), 10) || 0;
            var duration = 1400;
            var start = null;

            function step(timestamp) {
                if (!start) start = timestamp;
                var progress = Math.min((timestamp - start) / duration, 1);
                var eased = 1 - Math.pow(1 - progress, 3);
                el.textContent = Math.floor(eased * target).toLocaleString();
                if (progress < 1) requestAnimationFrame(step);
                else el.textContent = target.toLocaleString();
            }
            requestAnimationFrame(step);
        }
    }

    /* -----------------------------------------------------------------------
       REVELATION AU DEFILEMENT
    ----------------------------------------------------------------------- */
    function initScrollReveal() {
        var targets = document.querySelectorAll('.service-card, .news-card, .stat-box, .kpi-card');
        if (!targets.length || !window.IntersectionObserver) return;
        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-in');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1 });
        targets.forEach(function (el) { observer.observe(el); });
    }

    /* -----------------------------------------------------------------------
       AFFICHAGE / MASQUAGE DU MOT DE PASSE
    ----------------------------------------------------------------------- */
    function initPasswordToggles() {
        document.querySelectorAll('.password-toggle').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var input = btn.closest('.password-field').querySelector('input');
                var icon = btn.querySelector('i');
                if (!input) return;
                var isPassword = input.type === 'password';
                input.type = isPassword ? 'text' : 'password';
                if (icon) icon.className = isPassword ? 'bi bi-eye-slash' : 'bi bi-eye';
            });
        });
    }

    /* -----------------------------------------------------------------------
       INDICATEUR DE FORCE DU MOT DE PASSE (formulaire d'inscription)
    ----------------------------------------------------------------------- */
    function initPasswordStrength() {
        var wrap = document.querySelector('[data-strength-for]');
        if (!wrap) return;
        var fieldName = wrap.getAttribute('data-strength-for');
        var input = document.getElementById(fieldName) || document.querySelector('input[name="' + fieldName + '"]');
        var bar = wrap.querySelector('span');
        if (!input || !bar) return;

        input.addEventListener('input', function () {
            var value = input.value;
            var score = 0;
            if (value.length >= 8) score++;
            if (/[A-Z]/.test(value)) score++;
            if (/[0-9]/.test(value)) score++;
            if (/[^A-Za-z0-9]/.test(value)) score++;

            var colors = ['#C62828', '#D97706', '#D97706', '#1E8E5A', '#1E8E5A'];
            var widths = ['12%', '35%', '60%', '85%', '100%'];
            bar.style.width = value.length ? widths[score] : '0';
            bar.style.background = colors[score];
        });
    }

    /* -----------------------------------------------------------------------
       VALIDATION DES FORMULAIRES (Bootstrap style)
    ----------------------------------------------------------------------- */
    function initFormValidation() {
        document.querySelectorAll('form[data-validate]').forEach(function (form) {
            form.addEventListener('submit', function (evt) {
                if (!form.checkValidity()) {
                    evt.preventDefault();
                    evt.stopPropagation();
                }
                form.classList.add('was-validated');
            });
        });
    }

    /* -----------------------------------------------------------------------
       CONFIRMATION AVANT SUPPRESSION / ACTION SENSIBLE
    ----------------------------------------------------------------------- */
    function initDeleteConfirmations() {
        document.querySelectorAll('form[data-confirm]').forEach(function (form) {
            form.addEventListener('submit', function (evt) {
                var message = form.getAttribute('data-confirm');
                if (!window.confirm(message)) {
                    evt.preventDefault();
                }
            });
        });
    }

    /* -----------------------------------------------------------------------
       ZONE DE GLISSER-DEPOSER POUR LES PIECES JOINTES
    ----------------------------------------------------------------------- */
    function initFileDropZone() {
        var zone = document.getElementById('requestFileDropZone');
        var input = zone ? zone.querySelector('.file-drop-input') : null;
        var list = document.getElementById('requestFileList');
        if (!zone || !input) return;

        ['dragenter', 'dragover'].forEach(function (evtName) {
            zone.addEventListener(evtName, function (e) {
                e.preventDefault();
                zone.classList.add('dragover');
            });
        });
        ['dragleave', 'drop'].forEach(function (evtName) {
            zone.addEventListener(evtName, function (e) {
                e.preventDefault();
                zone.classList.remove('dragover');
            });
        });
        zone.addEventListener('drop', function (e) {
            if (e.dataTransfer && e.dataTransfer.files.length) {
                input.files = e.dataTransfer.files;
                renderFileList();
            }
        });
        input.addEventListener('change', renderFileList);

        function renderFileList() {
            if (!list) return;
            list.innerHTML = '';
            Array.prototype.forEach.call(input.files, function (file) {
                var li = document.createElement('li');
                li.innerHTML = '<i class="bi bi-file-earmark"></i> <span>' + escapeHtml(file.name) + '</span>';
                list.appendChild(li);
            });
        }
    }

    function escapeHtml(str) {
        var div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    /* -----------------------------------------------------------------------
       PREVISUALISATION DE L'AVATAR / IMAGES
    ----------------------------------------------------------------------- */
    function initAvatarPreview() {
        document.querySelectorAll('input[type="file"][data-preview]').forEach(function (input) {
            var previewEl = document.getElementById(input.getAttribute('data-preview'));
            if (!previewEl) return;
            input.addEventListener('change', function () {
                var file = input.files && input.files[0];
                if (!file) return;
                var reader = new FileReader();
                reader.onload = function (e) {
                    previewEl.src = e.target.result;
                    previewEl.classList.add('show');
                };
                reader.readAsDataURL(file);
            });
        });
    }

    /* -----------------------------------------------------------------------
       NOTIFICATIONS : MARQUER COMME LUE (AJAX)
    ----------------------------------------------------------------------- */
    function initNotificationMarkRead() {
        document.querySelectorAll('.notif-item').forEach(function (item) {
            item.addEventListener('click', function () {
                item.classList.remove('unread');
            });
        });
    }

    /* -----------------------------------------------------------------------
       VISIONNEUSE PDF : ZOOM, IMPRESSION, PLEIN ECRAN
    ----------------------------------------------------------------------- */
    function initPdfViewerControls() {
        var iframe = document.getElementById('pdfViewerIframe');
        var frameWrap = document.getElementById('pdfViewerFrame');
        var zoomInBtn = document.getElementById('pdfZoomIn');
        var zoomOutBtn = document.getElementById('pdfZoomOut');
        var printBtn = document.getElementById('pdfPrint');
        var fullscreenBtn = document.getElementById('pdfFullscreen');
        if (!iframe) return;

        var scale = 1;

        function applyZoom() {
            iframe.style.transform = 'scale(' + scale + ')';
            iframe.style.width = (100 / scale) + '%';
            iframe.style.height = (100 / scale) + '%';
        }

        if (zoomInBtn) zoomInBtn.addEventListener('click', function () {
            scale = Math.min(scale + 0.2, 2);
            applyZoom();
        });
        if (zoomOutBtn) zoomOutBtn.addEventListener('click', function () {
            scale = Math.max(scale - 0.2, 0.6);
            applyZoom();
        });
        if (printBtn) printBtn.addEventListener('click', function () {
            try {
                iframe.contentWindow.focus();
                iframe.contentWindow.print();
            } catch (e) {
                window.open(iframe.src, '_blank');
            }
        });
        if (fullscreenBtn) fullscreenBtn.addEventListener('click', function () {
            if (frameWrap.requestFullscreen) frameWrap.requestFullscreen();
            else if (frameWrap.webkitRequestFullscreen) frameWrap.webkitRequestFullscreen();
        });
    }

    /* -----------------------------------------------------------------------
       MODALES D'EDITION (ADMINISTRATION) : PRE-REMPLISSAGE DEPUIS data-*
    ----------------------------------------------------------------------- */
    function initAdminEditModals() {
        bindEditModal('userEditModal', 'userEditForm', {
            'first-name': 'e_first_name', 'last-name': 'e_last_name', 'email': 'e_email',
            'phone': 'e_phone', 'role-id': 'e_role_id', 'department-id': 'e_department_id',
        }, { active: 'e_is_active' });

        bindEditModal('deptEditModal', 'deptEditForm', {
            'name-fr': 'e_dept_name_fr', 'name-ar': 'e_dept_name_ar',
            'desc-fr': 'e_dept_desc_fr', 'desc-ar': 'e_dept_desc_ar',
        });

        bindEditModal('serviceEditModal', 'serviceEditForm', {
            'name-fr': 'e_svc_name_fr', 'name-ar': 'e_svc_name_ar',
            'desc-fr': 'e_svc_desc_fr', 'desc-ar': 'e_svc_desc_ar',
            'icon': 'e_svc_icon', 'order': 'e_svc_order', 'department-id': 'e_svc_department_id',
        }, { active: 'e_svc_active' });

        bindEditModal('newsEditModal', 'newsEditForm', {
            'title-fr': 'e_news_title_fr', 'title-ar': 'e_news_title_ar',
            'content-fr': 'e_news_content_fr', 'content-ar': 'e_news_content_ar',
        }, { active: 'e_news_active' });

        bindEditModal('docEditModal', 'docEditForm', {
            'title-fr': 'e_doc_title_fr', 'title-ar': 'e_doc_title_ar',
            'reference': 'e_doc_reference', 'category': 'e_doc_category',
            'service-id': 'e_doc_service_id',
        });
    }

    function bindEditModal(modalId, formId, fieldMap, checkboxMap) {
        var modalEl = document.getElementById(modalId);
        var formEl = document.getElementById(formId);
        if (!modalEl || !formEl) return;

        modalEl.addEventListener('show.bs.modal', function (event) {
            var button = event.relatedTarget;
            if (!button) return;

            var action = button.getAttribute('data-action');
            if (action) formEl.setAttribute('action', action);

            Object.keys(fieldMap).forEach(function (dataKey) {
                var value = button.getAttribute('data-' + dataKey);
                var targetId = fieldMap[dataKey];
                var target = document.getElementById(targetId);
                if (target && value !== null) target.value = value;
            });

            if (checkboxMap) {
                Object.keys(checkboxMap).forEach(function (dataKey) {
                    var value = button.getAttribute('data-' + dataKey);
                    var target = document.getElementById(checkboxMap[dataKey]);
                    if (target) target.checked = !!value;
                });
            }
        });
    }

    /* -----------------------------------------------------------------------
       PRE-SELECTION DU SERVICE LORS DE LA CREATION D'UNE DEMANDE
       (arrivee depuis la page d'un service via ?service=ID)
    ----------------------------------------------------------------------- */
    function initServiceRequestPrefill() {
        var select = document.getElementById('requestServiceSelect');
        if (!select) return;
        var params = new URLSearchParams(window.location.search);
        var serviceId = params.get('service');
        if (serviceId) select.value = serviceId;
    }

    /* -----------------------------------------------------------------------
       RECHERCHE INSTANTANEE DANS UN TABLEAU (ex : documents en administration)
       Filtre les lignes portant un attribut data-search en fonction de la
       saisie d'un champ marque data-table-search="<id-du-tableau>".
    ----------------------------------------------------------------------- */
    function initTableSearch() {
        document.querySelectorAll('[data-table-search]').forEach(function (input) {
            var table = document.getElementById(input.getAttribute('data-table-search'));
            if (!table) return;
            var rows = table.querySelectorAll('tbody tr[data-search]');

            input.addEventListener('input', function () {
                var term = input.value.trim().toLowerCase();
                var visibleCount = 0;
                rows.forEach(function (row) {
                    var match = row.getAttribute('data-search').indexOf(term) !== -1;
                    row.style.display = match ? '' : 'none';
                    if (match) visibleCount++;
                });
                table.classList.toggle('table-empty-search', term.length > 0 && visibleCount === 0);
            });
        });
    }

    /* Expose getCsrfToken globally in case future inline scripts need it */
    window.PDSC = { getCsrfToken: getCsrfToken };
})();
