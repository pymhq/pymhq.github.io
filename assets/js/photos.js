/* ============================================================
   photos.js: the viewer on the photograph collection pages.

   Extracted from photos/events/index.html alongside photos.css, for the same
   reason. It looks for a .sheet and returns quietly when there is none, so
   including it from any collection page is safe.
   ============================================================ */

/* Contact-sheet viewer.

   Click, Enter or Space on a frame opens it; Escape closes; the
   arrow keys and the two on-screen arrows step through the sheet in
   document order, which is chronological.

   The caption is cloned from the frame rather than rebuilt, so the
   viewer inherits the same bilingual span pairs. shell.js owns
   language visibility, so after inserting a clone we ask it to
   re-apply the current choice. Otherwise a reader in Chinese would
   get the English line back inside the viewer. */
(function () {
   'use strict';

   var lb = document.getElementById('lb');
   var lbImg = document.getElementById('lb-img');
   var lbCap = document.getElementById('lb-cap');
   var frames = Array.prototype.slice.call(
      document.querySelectorAll('.sheet .frame')
   );
   if (!lb || !frames.length) return;

   var at = -1;
   var opener = null;

   function show(i) {
      at = (i + frames.length) % frames.length;
      var fig = frames[at];
      var img = fig.querySelector('img');

      // data-full names the widest derivative that exists for this
      // frame. currentSrc is whatever the srcset picked for a 350px
      // column, which is the wrong file to enlarge.
      lbImg.src = img.dataset.full || img.currentSrc || img.src;
      lbImg.alt = img.alt;

      // The metadata lives on the occasion, not the frame, so the
      // viewer clones the occasion header and appends the frame's own
      // credit where it has one.
      //
      // A deep clone carries the hidden attribute shell.js has
      // already set on each lang span, so the caption arrives in
      // whichever language the reader is in. A later switch is
      // covered too: applyLanguage queries the whole document, and
      // this clone is inside it. Nothing here needs to re-run it.
      var head = fig.closest('.occasion').querySelector('.occ-head');
      // Either kind of frame caption: .f-credit names a person,
      // .f-caption says what the photograph is of. Selecting only the
      // first meant a caption never reached the viewer at all.
      var credit = fig.querySelector('.f-credit, .f-caption');
      lbCap.replaceChildren(head.cloneNode(true));
      if (credit) lbCap.appendChild(credit.cloneNode(true));

      // "3 / 23" is the only thing the viewer knows that the page
      // does not already say.
      var count = document.createElement('p');
      count.className = 'lb-count';
      count.textContent = (at + 1) + ' / ' + frames.length;
      lbCap.appendChild(count);
   }

   function open(i, from) {
      opener = from || null;
      show(i);
      lb.hidden = false;
      document.body.style.overflow = 'hidden';
      lb.querySelector('.lb-x').focus();
   }

   function close() {
      lb.hidden = true;
      lbImg.removeAttribute('src');
      document.body.style.overflow = '';
      if (opener) opener.focus();
   }

   frames.forEach(function (fig, i) {
      // A figure is not focusable and not a button; give it both
      // properties by hand rather than wrapping the image in an
      // anchor, which would make the caption links nest.
      fig.tabIndex = 0;
      fig.setAttribute('role', 'button');
      fig.setAttribute('aria-haspopup', 'dialog');

      fig.addEventListener('click', function (e) {
         // Caption links keep working: only the frame itself opens
         // the viewer.
         if (e.target.closest('a')) return;
         open(i, fig);
      });

      fig.addEventListener('keydown', function (e) {
         if (e.target.closest('a')) return;
         if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            open(i, fig);
         }
      });
   });

   lb.addEventListener('click', function (e) {
      var step = e.target.closest('[data-lb-step]');
      if (step) {
         show(at + Number(step.dataset.lbStep));
         return;
      }
      // Anywhere off the picture closes, including the backdrop and
      // the explicit close button.
      if (e.target.closest('[data-lb-close]') || !e.target.closest('.lb-stage')) {
         close();
      }
   });

   document.addEventListener('keydown', function (e) {
      if (lb.hidden) return;
      if (e.key === 'Escape') { close(); }
      else if (e.key === 'ArrowLeft') { show(at - 1); }
      else if (e.key === 'ArrowRight') { show(at + 1); }
   });
})();
