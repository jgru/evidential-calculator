;; -*- lexical-binding: t -*-

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; Bootstrap use-package
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

;; ;; Disable verbose warnings related to native-compilation
;; (require 'comp nil t)
;; (when (fboundp 'native-compile)
;;     (setq native-comp-async-report-warnings-errors nil))

(require 'package)
(add-to-list 'package-archives '("gnu"   . "https://elpa.gnu.org/packages/"))
(add-to-list 'package-archives '("melpa" . "https://melpa.org/packages/"))
(package-initialize)

(unless (package-installed-p 'use-package)
  (package-refresh-contents)
  (package-install 'use-package))
(eval-and-compile
  (setq use-package-always-ensure t
        use-package-expand-minimally t))

(setq byte-compile-error-on-warn nil)

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; General Tweaks (Behaviour and UI)
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(use-package emacs
  :ensure nil
  :config
  ;; Confirm shutdown
  (setq confirm-kill-emacs #'yes-or-no-p)
  ;; Change yes or no to y or n
  (fset 'yes-or-no-p 'y-or-n-p)
  ;; speed up movement apparently : https://emacs.stackexchange.com/a/28746/8964
  (setq auto-window-vscroll nil)
  ;; no startup msg
  (setq inhibit-startup-message t)
  ;; inhibit start screen
  (setq inhibit-startup-screen t)
  ;; Don't have backups, cause YOLO
  (setq backup-inhibited t)
  ;; don't accelerate scrolling
  (setq mouse-wheel-progressive-speed nil)
  ;; keyboard scroll one line at a time
  (setq scroll-step 1)
  ;; saves typing
  (define-key global-map (kbd "RET") 'newline-and-indent)
  ;; echo to screen faster for the snappy experience
  (setq echo-keystrokes 0.01)
  ;;show-paren-mode allows one to see matching pairs of parentheses and other characters
  (show-paren-mode t)
  ;; Shrink line spacing
  (setq-default line-spacing 0)
  ;; Don't save anything.
  (setq auto-save-default nil)
  ;; No audible beep
  (setq visible-bell t)
  ;; Do not end senteces with double space
  (setq sentence-end-double-space nil)
  (setq fill-column 70))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; Themeing
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
(load-theme 'tango-dark t)

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; Orgmode tweaks
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

;; Follow "Github-flavored links" in ToCs
(use-package toc-org
  :ensure t
  :hook
  (org-mode . toc-org-mode))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; Literate Programming
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(use-package ob
  :ensure nil ;; already part of org-contrib
  :after org
  :config
  (setq org-babel-load-languages
        '((python . t)
          (emacs-lisp . t)
          (shell . t)))

   ;; Load the languages
   (org-babel-do-load-languages 'org-babel-load-languages org-babel-load-languages)

   (setq org-babel-python-command "python3")

   ;; Syntax highlighting in src-blocks
   (setq org-src-fontify-natively t)

   ;; Start code on same pos as #+begin...
   (setq org-edit-src-content-indentation 0)

   ;; Use C-c C-c to execute
   (setq org-babel-no-eval-on-ctrl-c-ctrl-c nil)

   ;; C-c C-c should run the could without confirmation
   (setq org-confirm-babel-evaluate nil)
   :hook
   (org-babel-after-execute . org-redisplay-inline-images)
  :bind (:map org-mode-map
  ("C-c k" . org-babel-remove-result)))

(use-package python-mode
  :mode ("\\.py\\'" . python-mode)
  :init
  (setq python-shell-interpreter (executable-find "python3"))
  (setq python-shell-completion-native-enable nil)
  :config
  (setq python-indent 4))

;; Ease switching Python virtual environments
;; via the menu bar or with `pyvenv-workon`
;; Setting the `WORKON_HOME` environment variable points
;; at where the envs are located.
(use-package pyvenv
  :ensure t
  :defer t
  :config
  ;; Setting work on to easily switch between environments
  (setenv "WORKON_HOME" (expand-file-name "~/"))
  ;; Display virtual envs in the menu bar
  (setq pyvenv-menu t)
  ;; Set correct Python interpreter after (de)activating a venv
  (setq pyvenv-post-activate-hooks
        (list (lambda ()
                (setq python-shell-interpreter (concat pyvenv-virtual-env "bin/python3.9"))
                (pyvenv-restart-python))))
  (setq pyvenv-post-deactivate-hooks
        (list (lambda ()
                (setq python-shell-interpreter "python3.9"))))

  :hook (python-mode . pyvenv-mode))

;; Open the literate examples by default
(setq default-directory "/usr/local/src/evidential-calculator/examples")
(find-file "/usr/local/src/evidential-calculator/examples/lst-1.org")
