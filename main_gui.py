import os
import sys
import queue
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText

# 코어 비즈니스 로직 임포트
import hwp_core


class HwpToolkitApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("한글 문서 통합 관리자 (HWP Toolkit) v1.0")
        self.root.geometry("1000 concealed".replace(" concealed", "x820"))
        self.root.minsize(880, 680)

        # 로그 및 진행률 통신용 큐
        self.msg_queue = queue.Queue()
        self.is_running = False
        self.cancel_requested = False

        # 탭별 데이터 보관
        # 탭 1 (일괄 병합)
        self.merge_files = []
        # 탭 2 (최신순 증분)
        self.prepend_new_files = []
        # 탭 3 (기간별 추출)
        self.extract_doc_list = []
        self.extract_matched_docs = []
        # 탭 4 (파일명 변경)
        self.rename_files = []
        self.rename_plan = []

        self._apply_styles()
        self._build_ui()
        self._poll_queue()

    def _apply_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        base_font = ("맑은 고딕", 9)
        bold_font = ("맑은 고딕", 10, "bold")
        btn_font = ("맑은 고딕", 10, "bold")

        style.configure(".", font=base_font)
        style.configure("TNotebook", background="#F1F5F9", borderwidth=0, tabmargins=[6, 6, 6, 0])
        style.configure("TNotebook.Tab",
                        font=bold_font,
                        padding=[20, 9],
                        focuscolor="")

        # 선택된 탭과 비선택 탭의 크기(padding)를 동일하게 고정하고 배경색/글자색으로만 명확히 구분
        style.map("TNotebook.Tab",
                  padding=[("selected", [20, 9]), ("!selected", [20, 9])],
                  background=[("selected", "#2563EB"), ("active", "#CBD5E1"), ("!selected", "#E2E8F0")],
                  foreground=[("selected", "#FFFFFF"), ("active", "#1E293B"), ("!selected", "#475569")],
                  lightcolor=[("selected", "#3B82F6"), ("!selected", "#F1F5F9")],
                  bordercolor=[("selected", "#1D4ED8"), ("!selected", "#CBD5E1")],
                  darkcolor=[("selected", "#1E40AF"), ("!selected", "#94A3B8")])

        style.configure("Primary.TButton", font=btn_font, foreground="#FFFFFF", background="#1976D2", padding=[14, 8])
        style.map("Primary.TButton",
                  background=[("active", "#1565C0"), ("disabled", "#B0BEC5")],
                  foreground=[("disabled", "#FFFFFF")])

        style.configure("Secondary.TButton", font=base_font, padding=[8, 4])
        style.configure("Danger.TButton", font=bold_font, foreground="#FFFFFF", background="#D32F2F", padding=[10, 6])
        style.map("Danger.TButton", background=[("active", "#B71C1C"), ("disabled", "#E57373")])

        style.configure("Treeview.Heading", font=bold_font, background="#ECEFF1")
        style.configure("Treeview", font=base_font, rowheight=24)

    def _build_ui(self):
        # 상단 헤더 프레임
        header_frame = tk.Frame(self.root, bg="#1E3A8A", height=54)
        header_frame.pack(fill=tk.X, side=tk.TOP)
        header_frame.pack_propagate(False)

        title_lbl = tk.Label(header_frame, text="📄 HWP / HWPX 통합 관리 도구 (All-in-One)",
                             font=("맑은 고딕", 13, "bold"), fg="#FFFFFF", bg="#1E3A8A")
        title_lbl.pack(side=tk.LEFT, padx=16, pady=10)

        sub_lbl = tk.Label(header_frame, text="HWP·HWPX 일괄 병합 | 최신순 증분 | 기간별 역추적 추출 | 파일명 일괄 변경",
                           font=("맑은 고딕", 9), fg="#93C5FD", bg="#1E3A8A")
        sub_lbl.pack(side=tk.RIGHT, padx=16, pady=10)

        # 메인 탭 컨테이너 (Notebook)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        # 4개 탭 생성
        self.tab_merge = ttk.Frame(self.notebook)
        self.tab_prepend = ttk.Frame(self.notebook)
        self.tab_extract = ttk.Frame(self.notebook)
        self.tab_rename = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_merge, text="  📑 문서 일괄 병합  ")
        self.notebook.add(self.tab_prepend, text="  ⚡ 최신순 증분 병합  ")
        self.notebook.add(self.tab_extract, text="  🔍 기간별 문서 추출  ")
        self.notebook.add(self.tab_rename, text="  🏷️ 파일명 일괄 변경  ")

        self._build_tab_merge()
        self._build_tab_prepend()
        self._build_tab_extract()
        self._build_tab_rename()

        # 하단 공통 진행 상태 및 로그 창
        self._build_bottom_panel()

    # --------------------------------------------------------------------------
    # 탭 1: 문서 일괄 병합
    # --------------------------------------------------------------------------
    def _build_tab_merge(self):
        # 버튼 바
        btn_bar = ttk.Frame(self.tab_merge)
        btn_bar.pack(fill=tk.X, padx=8, pady=6)

        ttk.Button(btn_bar, text="+ 파일 추가", style="Secondary.TButton",
                   command=self._merge_add_files).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_bar, text="+ 폴더 전체 추가", style="Secondary.TButton",
                   command=self._merge_add_folder).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_bar, text="▲ 위로", style="Secondary.TButton",
                   command=lambda: self._tree_move_item(self.merge_tree, self.merge_files, -1)).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_bar, text="▼ 아래로", style="Secondary.TButton",
                   command=lambda: self._tree_move_item(self.merge_tree, self.merge_files, 1)).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_bar, text="선택 삭제", style="Secondary.TButton",
                   command=self._merge_delete_selected).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_bar, text="전체 비우기", style="Secondary.TButton",
                   command=self._merge_clear).pack(side=tk.LEFT, padx=3)

        self.merge_count_lbl = ttk.Label(btn_bar, text="선택된 문서: 0개", font=("맑은 고딕", 9, "bold"))
        self.merge_count_lbl.pack(side=tk.RIGHT, padx=8)

        # 트리뷰 (파일 목록)
        tree_frame = ttk.Frame(self.tab_merge)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        columns = ("idx", "filename", "fmt", "path")
        self.merge_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="extended")
        self.merge_tree.heading("idx", text="순번")
        self.merge_tree.heading("filename", text="파일명")
        self.merge_tree.heading("fmt", text="형식")
        self.merge_tree.heading("path", text="전체 경로")

        self.merge_tree.column("idx", width=50, anchor="center")
        self.merge_tree.column("filename", width=280)
        self.merge_tree.column("fmt", width=70, anchor="center")
        self.merge_tree.column("path", width=450)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.merge_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.merge_tree.xview)
        self.merge_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.merge_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # 저장 위치 프레임
        save_frame = ttk.LabelFrame(self.tab_merge, text=" 저장 옵션 ")
        save_frame.pack(fill=tk.X, padx=8, pady=6)

        ttk.Label(save_frame, text="저장 파일 경로:").pack(side=tk.LEFT, padx=6, pady=6)
        self.merge_save_entry = ttk.Entry(save_frame)
        self.merge_save_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6, pady=6)
        default_save = os.path.abspath(os.path.join(os.getcwd(), "병합된_문서.hwpx"))
        self.merge_save_entry.insert(0, default_save)

        ttk.Button(save_frame, text="저장 위치 변경...", style="Secondary.TButton",
                   command=self._merge_browse_save).pack(side=tk.RIGHT, padx=6, pady=6)

        # 실행 버튼 프레임
        action_frame = ttk.Frame(self.tab_merge)
        action_frame.pack(fill=tk.X, padx=8, pady=4)

        info_lbl = ttk.Label(action_frame, text="※ 원본 서식(쪽/글자/문단/스타일) 보존 병합본과 초고속 검색용 TXT 파일이 동시 생성됩니다.",
                             foreground="#546E7A")
        info_lbl.pack(side=tk.LEFT, padx=6)

        self.merge_run_btn = ttk.Button(action_frame, text="▶ 일괄 병합 시작 (HWPX + TXT)",
                                        style="Primary.TButton", command=self._merge_run)
        self.merge_run_btn.pack(side=tk.RIGHT, padx=6)

    def _merge_add_files(self):
        paths = filedialog.askopenfilenames(
            title="병합할 한글 문서 선택",
            filetypes=[("한글 문서", "*.hwp;*.hwpx"), ("HWPX 파일", "*.hwpx"), ("HWP 파일", "*.hwp"), ("모든 파일", "*.*")]
        )
        if paths:
            for p in paths:
                p = os.path.abspath(p)
                if p not in self.merge_files:
                    self.merge_files.append(p)
            self._merge_refresh_tree()

    def _merge_add_folder(self):
        folder = filedialog.askdirectory(title="한글 문서가 있는 폴더 선택")
        if folder:
            added = 0
            for f in sorted(os.listdir(folder)):
                ext = os.path.splitext(f)[1].lower()
                if ext in [".hwp", ".hwpx"]:
                    full_p = os.path.abspath(os.path.join(folder, f))
                    if full_p not in self.merge_files:
                        self.merge_files.append(full_p)
                        added += 1
            self._merge_refresh_tree()
            self.log(f"폴더에서 {added}개의 한글 문서를 추가했습니다.")

    def _merge_refresh_tree(self):
        for item in self.merge_tree.get_children():
            self.merge_tree.delete(item)
        for idx, path in enumerate(self.merge_files, 1):
            fname = os.path.basename(path)
            fmt = hwp_core.get_file_format(path)
            self.merge_tree.insert("", "end", values=(f"{idx:03d}", fname, fmt, path))
        self.merge_count_lbl.config(text=f"선택된 문서: {len(self.merge_files)}개")

    def _merge_delete_selected(self):
        selected_items = self.merge_tree.selection()
        if not selected_items:
            return
        selected_indices = [self.merge_tree.index(i) for i in selected_items]
        self.merge_files = [p for idx, p in enumerate(self.merge_files) if idx not in selected_indices]
        self._merge_refresh_tree()

    def _merge_clear(self):
        self.merge_files.clear()
        self._merge_refresh_tree()

    def _merge_browse_save(self):
        curr = self.merge_save_entry.get().strip()
        init_dir = os.path.dirname(curr) if curr else os.getcwd()
        path = filedialog.asksaveasfilename(
            initialdir=init_dir,
            initialfile="병합된_문서.hwpx",
            defaultextension=".hwpx",
            filetypes=[("HWPX 파일", "*.hwpx"), ("HWP 파일", "*.hwp")]
        )
        if path:
            self.merge_save_entry.delete(0, tk.END)
            self.merge_save_entry.insert(0, os.path.abspath(path))

    def _merge_run(self):
        if not self.merge_files:
            messagebox.showwarning("안내", "병합할 문서를 1개 이상 추가해 주세요.")
            return
        save_path = self.merge_save_entry.get().strip()
        if not save_path:
            messagebox.showwarning("안내", "저장할 파일 경로를 지정해 주세요.")
            return

        files = list(self.merge_files)

        def worker():
            self._start_task("문서 일괄 병합 시작")
            try:
                hwp_core.merge_hwp_documents(
                    files, save_path,
                    log_fn=self.log,
                    progress_fn=self.progress,
                    cancel_check=lambda: self.cancel_requested
                )
                self.log("✨ [성공] 모든 문서 병합 작업이 완료되었습니다!")
                self.root.after(0, lambda: messagebox.showinfo("완료", f"병합 작업이 완료되었습니다!\n\n저장 위치: {save_path}"))
            except Exception as e:
                self.log(f"❌ [오류] {e}")
                self.root.after(0, lambda: messagebox.showerror("오류 발생", f"작업 중 오류가 발생했습니다:\n{e}"))
            finally:
                self._finish_task()

        threading.Thread(target=worker, daemon=True).start()

    # --------------------------------------------------------------------------
    # 탭 2: 최신순 맨 앞 증분 병합
    # --------------------------------------------------------------------------
    def _build_tab_prepend(self):
        # 1. 기존 대용량 파일 선택 영역
        base_box = ttk.LabelFrame(self.tab_prepend, text=" 1. 기존 대용량 병합본 선택 (HWPX / HWP) ")
        base_box.pack(fill=tk.X, padx=8, pady=6)

        self.prepend_base_entry = ttk.Entry(base_box)
        self.prepend_base_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6, pady=6)
        ttk.Button(base_box, text="파일 선택...", style="Secondary.TButton",
                   command=self._prepend_browse_base).pack(side=tk.RIGHT, padx=6, pady=6)

        # 2. 맨 앞에 추가할 신규 파일들
        new_box = ttk.LabelFrame(self.tab_prepend, text=" 2. 맨 앞에 최신순으로 추가할 신규 파일들 ")
        new_box.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        btn_bar2 = ttk.Frame(new_box)
        btn_bar2.pack(fill=tk.X, padx=6, pady=4)

        ttk.Button(btn_bar2, text="+ 신규 파일 추가", style="Secondary.TButton",
                   command=self._prepend_add_new_files).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_bar2, text="▲ 위로", style="Secondary.TButton",
                   command=lambda: self._tree_move_item(self.prepend_tree, self.prepend_new_files, -1)).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_bar2, text="▼ 아래로", style="Secondary.TButton",
                   command=lambda: self._tree_move_item(self.prepend_tree, self.prepend_new_files, 1)).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_bar2, text="선택 삭제", style="Secondary.TButton",
                   command=self._prepend_delete_selected).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_bar2, text="전체 비우기", style="Secondary.TButton",
                   command=self._prepend_clear).pack(side=tk.LEFT, padx=3)

        self.prepend_count_lbl = ttk.Label(btn_bar2, text="신규 파일: 0개", font=("맑은 고딕", 9, "bold"))
        self.prepend_count_lbl.pack(side=tk.RIGHT, padx=8)

        tree_frame2 = ttk.Frame(new_box)
        tree_frame2.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        cols = ("idx", "filename", "path")
        self.prepend_tree = ttk.Treeview(tree_frame2, columns=cols, show="headings", selectmode="extended")
        self.prepend_tree.heading("idx", text="순번")
        self.prepend_tree.heading("filename", text="신규 파일명 (맨 앞 삽입 순서)")
        self.prepend_tree.heading("path", text="전체 경로")

        self.prepend_tree.column("idx", width=50, anchor="center")
        self.prepend_tree.column("filename", width=340)
        self.prepend_tree.column("path", width=450)

        vsb2 = ttk.Scrollbar(tree_frame2, orient="vertical", command=self.prepend_tree.yview)
        self.prepend_tree.configure(yscrollcommand=vsb2.set)
        self.prepend_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb2.pack(side=tk.RIGHT, fill=tk.Y)

        # 3. 저장 위치
        save_box2 = ttk.LabelFrame(self.tab_prepend, text=" 3. 결과 저장 위치 지정 ")
        save_box2.pack(fill=tk.X, padx=8, pady=6)

        self.prepend_save_entry = ttk.Entry(save_box2)
        self.prepend_save_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6, pady=6)
        ttk.Button(save_box2, text="저장 위치 변경...", style="Secondary.TButton",
                   command=self._prepend_browse_save).pack(side=tk.RIGHT, padx=6, pady=6)

        # 4. 실행 바
        action_bar2 = ttk.Frame(self.tab_prepend)
        action_bar2.pack(fill=tk.X, padx=8, pady=4)

        tip2 = ttk.Label(action_bar2, text="💡 기존 대용량 문서를 단 1회만 결합하므로 수 초 만에 증분 병합이 완료됩니다.", foreground="#546E7A")
        tip2.pack(side=tk.LEFT, padx=6)

        self.prepend_run_btn = ttk.Button(action_bar2, text="▶ 최신순 증분 병합 시작",
                                          style="Primary.TButton", command=self._prepend_run)
        self.prepend_run_btn.pack(side=tk.RIGHT, padx=6)

    def _prepend_browse_base(self):
        path = filedialog.askopenfilename(
            title="기존 병합본 파일 선택",
            filetypes=[("한글 문서", "*.hwp;*.hwpx"), ("HWPX 파일", "*.hwpx"), ("HWP 파일", "*.hwp")]
        )
        if path:
            path = os.path.abspath(path)
            self.prepend_base_entry.delete(0, tk.END)
            self.prepend_base_entry.insert(0, path)

            base_dir = os.path.dirname(path)
            base_name, ext = os.path.splitext(os.path.basename(path))
            suggested = os.path.join(base_dir, f"{base_name}_최신추가{ext}")
            self.prepend_save_entry.delete(0, tk.END)
            self.prepend_save_entry.insert(0, suggested)

    def _prepend_add_new_files(self):
        paths = filedialog.askopenfilenames(
            title="맨 앞에 추가할 신규 파일 선택",
            filetypes=[("한글 문서", "*.hwp;*.hwpx"), ("모든 파일", "*.*")]
        )
        if paths:
            for p in paths:
                p = os.path.abspath(p)
                if p not in self.prepend_new_files:
                    self.prepend_new_files.append(p)
            self._prepend_refresh_tree()

    def _prepend_refresh_tree(self):
        for item in self.prepend_tree.get_children():
            self.prepend_tree.delete(item)
        for idx, path in enumerate(self.prepend_new_files, 1):
            fname = os.path.basename(path)
            self.prepend_tree.insert("", "end", values=(f"{idx:02d}", fname, path))
        self.prepend_count_lbl.config(text=f"신규 파일: {len(self.prepend_new_files)}개")

    def _prepend_delete_selected(self):
        selected_items = self.prepend_tree.selection()
        if not selected_items:
            return
        selected_indices = [self.prepend_tree.index(i) for i in selected_items]
        self.prepend_new_files = [p for idx, p in enumerate(self.prepend_new_files) if idx not in selected_indices]
        self._prepend_refresh_tree()

    def _prepend_clear(self):
        self.prepend_new_files.clear()
        self._prepend_refresh_tree()

    def _prepend_browse_save(self):
        curr = self.prepend_save_entry.get().strip()
        init_dir = os.path.dirname(curr) if curr else os.getcwd()
        path = filedialog.asksaveasfilename(
            initialdir=init_dir,
            initialfile=os.path.basename(curr) if curr else "병합본_최신추가.hwpx",
            defaultextension=".hwpx",
            filetypes=[("HWPX 파일", "*.hwpx"), ("HWP 파일", "*.hwp")]
        )
        if path:
            self.prepend_save_entry.delete(0, tk.END)
            self.prepend_save_entry.insert(0, os.path.abspath(path))

    def _prepend_run(self):
        base_file = self.prepend_base_entry.get().strip()
        if not base_file or not os.path.exists(base_file):
            messagebox.showwarning("안내", "기존 병합본 파일을 올바르게 선택해 주세요.")
            return
        if not self.prepend_new_files:
            messagebox.showwarning("안내", "맨 앞에 추가할 신규 파일을 1개 이상 선택해 주세요.")
            return
        save_path = self.prepend_save_entry.get().strip()
        if not save_path:
            messagebox.showwarning("안내", "결과물 저장 위치를 지정해 주세요.")
            return

        new_files = list(self.prepend_new_files)

        def worker():
            self._start_task("최신순 증분 병합 시작")
            try:
                hwp_core.prepend_hwp_documents(
                    base_file, new_files, save_path,
                    log_fn=self.log,
                    progress_fn=self.progress,
                    cancel_check=lambda: self.cancel_requested
                )
                self.log("✨ [성공] 최신순 증분 병합이 완료되었습니다!")
                self.root.after(0, lambda: messagebox.showinfo("완료", f"최신순 증분 병합이 완료되었습니다!\n\n저장 위치: {save_path}"))
            except Exception as e:
                self.log(f"❌ [오류] {e}")
                self.root.after(0, lambda: messagebox.showerror("오류 발생", f"작업 중 오류가 발생했습니다:\n{e}"))
            finally:
                self._finish_task()

        threading.Thread(target=worker, daemon=True).start()

    # --------------------------------------------------------------------------
    # 탭 3: 기간별 문서 역추적 추출
    # --------------------------------------------------------------------------
    def _build_tab_extract(self):
        # 1. 문서 선택 및 분석
        top_box = ttk.LabelFrame(self.tab_extract, text=" 1. 통합 병합 문서 선택 (동일 이름의 .txt 파일 자동 분석) ")
        top_box.pack(fill=tk.X, padx=8, pady=6)

        f_row = ttk.Frame(top_box)
        f_row.pack(fill=tk.X, padx=6, pady=4)

        self.extract_file_entry = ttk.Entry(f_row)
        self.extract_file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        ttk.Button(f_row, text="문서 선택...", style="Secondary.TButton",
                   command=self._extract_browse_doc).pack(side=tk.LEFT, padx=3)
        ttk.Button(f_row, text="분석 / 스캔", style="Secondary.TButton",
                   command=self._extract_analyze_doc).pack(side=tk.LEFT, padx=3)

        self.extract_info_lbl = ttk.Label(top_box, text="분석 대기 중: 전체 병합 문서를 선택하세요.",
                                          foreground="#1565C0", font=("맑은 고딕", 9, "bold"))
        self.extract_info_lbl.pack(anchor="w", padx=10, pady=2)

        # 2. 기간 입력 및 필터링
        period_box = ttk.LabelFrame(self.tab_extract, text=" 2. 추출할 기간 설정 (예: 2024 ~ 2026, 2025, 2024-03 ~ 2025-10, 2024 ~) ")
        period_box.pack(fill=tk.X, padx=8, pady=4)

        p_row = ttk.Frame(period_box)
        p_row.pack(fill=tk.X, padx=6, pady=4)

        ttk.Label(p_row, text="기간 입력:").pack(side=tk.LEFT, padx=4)
        self.extract_period_entry = ttk.Entry(p_row, width=28)
        self.extract_period_entry.pack(side=tk.LEFT, padx=4)
        self.extract_period_entry.insert(0, "2024 ~ 2026")

        ttk.Button(p_row, text="🔍 대상 문서 필터링", style="Secondary.TButton",
                   command=self._extract_filter_preview).pack(side=tk.LEFT, padx=6)

        # 3. 추출 대상 미리보기 트리뷰
        preview_box = ttk.LabelFrame(self.tab_extract, text=" 3. 추출 대상 문서 미리보기 ")
        preview_box.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        tree_f3 = ttk.Frame(preview_box)
        tree_f3.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        cols3 = ("idx", "date", "filename", "exist", "path")
        self.extract_tree = ttk.Treeview(tree_f3, columns=cols3, show="headings", selectmode="extended")
        self.extract_tree.heading("idx", text="순번")
        self.extract_tree.heading("date", text="추출 연월")
        self.extract_tree.heading("filename", text="파일명")
        self.extract_tree.heading("exist", text="원본 상태")
        self.extract_tree.heading("path", text="원본 파일 경로")

        self.extract_tree.column("idx", width=45, anchor="center")
        self.extract_tree.column("date", width=80, anchor="center")
        self.extract_tree.column("filename", width=280)
        self.extract_tree.column("exist", width=80, anchor="center")
        self.extract_tree.column("path", width=380)

        vsb3 = ttk.Scrollbar(tree_f3, orient="vertical", command=self.extract_tree.yview)
        self.extract_tree.configure(yscrollcommand=vsb3.set)
        self.extract_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb3.pack(side=tk.RIGHT, fill=tk.Y)

        # 4. 저장 위치 및 실행
        save_box3 = ttk.Frame(self.tab_extract)
        save_box3.pack(fill=tk.X, padx=8, pady=4)

        ttk.Label(save_box3, text="추출 저장 경로:").pack(side=tk.LEFT, padx=4)
        self.extract_save_entry = ttk.Entry(save_box3)
        self.extract_save_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        ttk.Button(save_box3, text="저장 위치 변경...", style="Secondary.TButton",
                   command=self._extract_browse_save).pack(side=tk.LEFT, padx=4)

        self.extract_run_btn = ttk.Button(save_box3, text="▶ 기간별 문서 추출 시작",
                                          style="Primary.TButton", command=self._extract_run)
        self.extract_run_btn.pack(side=tk.RIGHT, padx=4)

    def _extract_browse_doc(self):
        path = filedialog.askopenfilename(
            title="전체 병합 문서 또는 TXT 파일 선택",
            filetypes=[("병합 파일 (TXT / HWPX / HWP)", "*.txt;*.hwpx;*.hwp"), ("모든 파일", "*.*")]
        )
        if path:
            self.extract_file_entry.delete(0, tk.END)
            self.extract_file_entry.insert(0, os.path.abspath(path))
            self._extract_analyze_doc()

    def _extract_analyze_doc(self):
        doc_path = self.extract_file_entry.get().strip()
        if not doc_path or not os.path.exists(doc_path):
            messagebox.showwarning("안내", "유효한 파일을 선택해 주세요.")
            return

        ext = os.path.splitext(doc_path)[1].lower()
        if ext == ".txt":
            txt_path = doc_path
        else:
            txt_candidate = os.path.splitext(doc_path)[0] + ".txt"
            if os.path.exists(txt_candidate):
                txt_path = txt_candidate
            else:
                messagebox.showinfo("안내", f"동일 이름의 .txt 파일이 없습니다. 목록이 담긴 .txt 파일을 직접 선택하세요.")
                txt_path = filedialog.askopenfilename(title="병합 텍스트(.txt) 파일 선택", filetypes=[("텍스트", "*.txt")])
                if not txt_path:
                    return

        try:
            self.extract_doc_list = hwp_core.parse_merged_txt(txt_path)
            self.extract_txt_path = txt_path
            if not self.extract_doc_list:
                self.extract_info_lbl.config(text="[오류] 텍스트 파일에서 문서 정보를 찾을 수 없습니다.")
                return

            valid_dates = [d["date"] for d in self.extract_doc_list if d["date"]]
            min_d = min(valid_dates) if valid_dates else "미상"
            max_d = max(valid_dates) if valid_dates else "미상"

            self.extract_info_lbl.config(
                text=f"분석 완료: 총 {len(self.extract_doc_list)}개 문서 확인 | 전체 기간 범위: {min_d} ~ {max_d}"
            )
            self.log(f"통합 문서 분석 완료: {os.path.basename(txt_path)} (총 {len(self.extract_doc_list)}개 문서, {min_d}~{max_d})")
            self._extract_filter_preview()
        except Exception as e:
            messagebox.showerror("분석 오류", str(e))

    def _extract_filter_preview(self):
        if not self.extract_doc_list:
            return

        period_text = self.extract_period_entry.get().strip()
        start_d, end_d = hwp_core.parse_period_input(period_text)
        if not start_d:
            messagebox.showwarning("입력 오류", "기간 형식을 올바르게 입력해 주세요.\n예: 2024 ~ 2026, 2025, 2024-03 ~ 2025-10")
            return

        self.extract_matched_docs = [
            d for d in self.extract_doc_list
            if d["date"] and (start_d <= d["date"] <= end_d)
        ]

        for item in self.extract_tree.get_children():
            self.extract_tree.delete(item)

        for idx, doc in enumerate(self.extract_matched_docs, 1):
            exists_str = "존재" if os.path.exists(doc["filepath"]) else "누락(X)"
            self.extract_tree.insert("", "end", values=(
                f"{idx:02d}", doc["date"], doc["filename"], exists_str, doc["filepath"]
            ))

        base_dir = os.path.dirname(self.extract_txt_path)
        base_name = os.path.splitext(os.path.basename(self.extract_txt_path))[0]
        period_tag = period_text.replace(" ", "").replace("~", "-")
        suggested = os.path.join(base_dir, f"{base_name}_{period_tag}.hwpx")
        self.extract_save_entry.delete(0, tk.END)
        self.extract_save_entry.insert(0, suggested)

        self.log(f"기간 [{start_d} ~ {end_d}] 필터링: 총 {len(self.extract_matched_docs)}개 문서 검색됨")

    def _extract_browse_save(self):
        curr = self.extract_save_entry.get().strip()
        init_dir = os.path.dirname(curr) if curr else os.getcwd()
        path = filedialog.asksaveasfilename(
            initialdir=init_dir,
            initialfile=os.path.basename(curr) if curr else "추출문서.hwpx",
            defaultextension=".hwpx",
            filetypes=[("HWPX 파일", "*.hwpx"), ("HWP 파일", "*.hwp")]
        )
        if path:
            self.extract_save_entry.delete(0, tk.END)
            self.extract_save_entry.insert(0, os.path.abspath(path))

    def _extract_run(self):
        if not self.extract_matched_docs:
            messagebox.showwarning("안내", "추출할 대상 문서가 없습니다. 먼저 기간을 필터링하세요.")
            return
        save_path = self.extract_save_entry.get().strip()
        if not save_path:
            messagebox.showwarning("안내", "저장 위치를 지정해 주세요.")
            return

        period_text = self.extract_period_entry.get().strip()
        start_d, end_d = hwp_core.parse_period_input(period_text)
        txt_path = self.extract_txt_path
        matched = list(self.extract_matched_docs)

        def worker():
            self._start_task("기간별 문서 역추적 추출 시작")
            try:
                hwp_core.extract_period_documents(
                    txt_path, matched, period_text, start_d, end_d, save_path,
                    log_fn=self.log,
                    progress_fn=self.progress,
                    cancel_check=lambda: self.cancel_requested
                )
                self.log("✨ [성공] 기간별 문서 추출 및 병합이 완료되었습니다!")
                self.root.after(0, lambda: messagebox.showinfo("완료", f"기간별 문서 추출이 완료되었습니다!\n\n저장 위치: {save_path}"))
            except Exception as e:
                self.log(f"❌ [오류] {e}")
                self.root.after(0, lambda: messagebox.showerror("오류 발생", f"추출 중 오류가 발생했습니다:\n{e}"))
            finally:
                self._finish_task()

        threading.Thread(target=worker, daemon=True).start()

    # --------------------------------------------------------------------------
    # 탭 4: 파일명 일괄 변경 (Batch Renamer)
    # --------------------------------------------------------------------------
    def _build_tab_rename(self):
        # 1. 상단 파일/폴더 선택
        top_f = ttk.Frame(self.tab_rename)
        top_f.pack(fill=tk.X, padx=8, pady=6)

        ttk.Button(top_f, text="+ 파일 다중 선택", style="Secondary.TButton",
                   command=self._rename_add_files).pack(side=tk.LEFT, padx=3)
        ttk.Button(top_f, text="+ 대상 폴더 선택", style="Secondary.TButton",
                   command=self._rename_add_folder).pack(side=tk.LEFT, padx=3)
        ttk.Button(top_f, text="목록 비우기", style="Secondary.TButton",
                   command=self._rename_clear).pack(side=tk.LEFT, padx=3)

        self.rename_count_lbl = ttk.Label(top_f, text="대상 파일: 0개", font=("맑은 고딕", 9, "bold"))
        self.rename_count_lbl.pack(side=tk.RIGHT, padx=8)

        # 2. 규칙 선택 프레임
        rule_box = ttk.LabelFrame(self.tab_rename, text=" 변경 규칙 선택 ")
        rule_box.pack(fill=tk.X, padx=8, pady=4)

        self.rename_rule_var = tk.StringVar(value="remove_copy")

        r1 = ttk.Radiobutton(rule_box, text="1. 윈도우 복사본 접미사 일괄 삭제 ('의 사본', '- 복사본', 'Copy' 등) [원클릭]",
                             variable=self.rename_rule_var, value="remove_copy", command=self._rename_update_plan)
        r1.grid(row=0, column=0, columnspan=4, sticky="w", padx=6, pady=3)

        r2 = ttk.Radiobutton(rule_box, text="2. 문자열 찾아 바꾸기:",
                             variable=self.rename_rule_var, value="replace", command=self._rename_update_plan)
        r2.grid(row=1, column=0, sticky="w", padx=6, pady=3)
        ttk.Label(rule_box, text="찾을 말:").grid(row=1, column=1, sticky="e")
        self.rename_old_entry = ttk.Entry(rule_box, width=15)
        self.rename_old_entry.grid(row=1, column=2, sticky="w", padx=3)
        ttk.Label(rule_box, text="바꿀 말:").grid(row=1, column=3, sticky="e")
        self.rename_new_entry = ttk.Entry(rule_box, width=15)
        self.rename_new_entry.grid(row=1, column=4, sticky="w", padx=3)

        r3 = ttk.Radiobutton(rule_box, text="3. 접두사 / 접미사 추가:",
                             variable=self.rename_rule_var, value="affix", command=self._rename_update_plan)
        r3.grid(row=2, column=0, sticky="w", padx=6, pady=3)
        ttk.Label(rule_box, text="맨 앞(접두):").grid(row=2, column=1, sticky="e")
        self.rename_prefix_entry = ttk.Entry(rule_box, width=15)
        self.rename_prefix_entry.grid(row=2, column=2, sticky="w", padx=3)
        ttk.Label(rule_box, text="맨 뒤(접미):").grid(row=2, column=3, sticky="e")
        self.rename_suffix_entry = ttk.Entry(rule_box, width=15)
        self.rename_suffix_entry.grid(row=2, column=4, sticky="w", padx=3)

        r4 = ttk.Radiobutton(rule_box, text="4. 모의고사 날짜 표준화 (예: 2026년 9월 -> [2026-09], 2025.06 -> [2025-06])",
                             variable=self.rename_rule_var, value="mock_date", command=self._rename_update_plan)
        r4.grid(row=3, column=0, columnspan=4, sticky="w", padx=6, pady=3)

        r5 = ttk.Radiobutton(rule_box, text="5. 정규표현식 치환:",
                             variable=self.rename_rule_var, value="regex", command=self._rename_update_plan)
        r5.grid(row=4, column=0, sticky="w", padx=6, pady=3)
        ttk.Label(rule_box, text="패턴(Regex):").grid(row=4, column=1, sticky="e")
        self.rename_regex_pat = ttk.Entry(rule_box, width=15)
        self.rename_regex_pat.grid(row=4, column=2, sticky="w", padx=3)
        ttk.Label(rule_box, text="대체식:").grid(row=4, column=3, sticky="e")
        self.rename_regex_repl = ttk.Entry(rule_box, width=15)
        self.rename_regex_repl.grid(row=4, column=4, sticky="w", padx=3)

        r6 = ttk.Radiobutton(rule_box, text="6. 순차 번호 매기기 (01_, 02_...):",
                             variable=self.rename_rule_var, value="numbering", command=self._rename_update_plan)
        r6.grid(row=5, column=0, sticky="w", padx=6, pady=3)
        ttk.Label(rule_box, text="구분자:").grid(row=5, column=1, sticky="e")
        self.rename_num_sep = ttk.Entry(rule_box, width=6)
        self.rename_num_sep.insert(0, "_ ")
        self.rename_num_sep.grid(row=5, column=2, sticky="w", padx=3)

        ttk.Button(rule_box, text="🔄 미리보기 새로고침", style="Secondary.TButton",
                   command=self._rename_update_plan).grid(row=5, column=4, sticky="e", padx=6, pady=3)

        # 3. 변경 전/후 비교 미리보기 트리뷰
        preview_box4 = ttk.LabelFrame(self.tab_rename, text=" 변경 미리보기 (초록색: 변경 예정) ")
        preview_box4.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        tree_f4 = ttk.Frame(preview_box4)
        tree_f4.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        cols4 = ("status", "old_name", "new_name", "path")
        self.rename_tree = ttk.Treeview(tree_f4, columns=cols4, show="headings", selectmode="extended")
        self.rename_tree.heading("status", text="상태")
        self.rename_tree.heading("old_name", text="현재 파일명")
        self.rename_tree.heading("new_name", text="변경될 새 파일명")
        self.rename_tree.heading("path", text="폴더 경로")

        self.rename_tree.column("status", width=70, anchor="center")
        self.rename_tree.column("old_name", width=330)
        self.rename_tree.column("new_name", width=330)
        self.rename_tree.column("path", width=200)

        # 색상 태그
        self.rename_tree.tag_configure("changed", background="#E8F5E9", foreground="#2E7D32")
        self.rename_tree.tag_configure("unchanged", foreground="#78909C")

        vsb4 = ttk.Scrollbar(tree_f4, orient="vertical", command=self.rename_tree.yview)
        self.rename_tree.configure(yscrollcommand=vsb4.set)
        self.rename_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb4.pack(side=tk.RIGHT, fill=tk.Y)

        # 4. 실행 버튼
        action_bar4 = ttk.Frame(self.tab_rename)
        action_bar4.pack(fill=tk.X, padx=8, pady=4)

        self.rename_change_stat_lbl = ttk.Label(action_bar4, text="변경 예정: 0개 / 유지: 0개",
                                                font=("맑은 고딕", 9, "bold"))
        self.rename_change_stat_lbl.pack(side=tk.LEFT, padx=6)

        self.rename_run_btn = ttk.Button(action_bar4, text="▶ 파일명 일괄 변경 적용",
                                         style="Primary.TButton", command=self._rename_run)
        self.rename_run_btn.pack(side=tk.RIGHT, padx=6)

    def _rename_add_files(self):
        paths = filedialog.askopenfilenames(
            title="이름을 변경할 파일 선택",
            filetypes=[("모든 파일", "*.*"), ("한글 문서", "*.hwp;*.hwpx")]
        )
        if paths:
            for p in paths:
                p = os.path.abspath(p)
                if p not in self.rename_files:
                    self.rename_files.append(p)
            self._rename_update_plan()

    def _rename_add_folder(self):
        folder = filedialog.askdirectory(title="이름을 변경할 파일들이 있는 폴더 선택")
        if folder:
            added = 0
            for f in sorted(os.listdir(folder)):
                full_p = os.path.abspath(os.path.join(folder, f))
                if os.path.isfile(full_p) and full_p not in self.rename_files:
                    self.rename_files.append(full_p)
                    added += 1
            self._rename_update_plan()
            self.log(f"폴더에서 {added}개 파일을 불러왔습니다.")

    def _rename_clear(self):
        self.rename_files.clear()
        self.rename_plan.clear()
        for item in self.rename_tree.get_children():
            self.rename_tree.delete(item)
        self.rename_count_lbl.config(text="대상 파일: 0개")
        self.rename_change_stat_lbl.config(text="변경 예정: 0개 / 유지: 0개")

    def _rename_update_plan(self):
        if not self.rename_files:
            return

        mode = self.rename_rule_var.get()
        kwargs = {}
        if mode == "replace":
            kwargs["old_str"] = self.rename_old_entry.get()
            kwargs["new_str"] = self.rename_new_entry.get()
        elif mode == "affix":
            kwargs["prefix"] = self.rename_prefix_entry.get()
            kwargs["suffix"] = self.rename_suffix_entry.get()
        elif mode == "regex":
            kwargs["pattern"] = self.rename_regex_pat.get()
            kwargs["repl"] = self.rename_regex_repl.get()
        elif mode == "numbering":
            kwargs["sep"] = self.rename_num_sep.get()

        self.rename_plan = hwp_core.generate_rename_plan(self.rename_files, mode, **kwargs)

        for item in self.rename_tree.get_children():
            self.rename_tree.delete(item)

        changed_cnt = 0
        for item in self.rename_plan:
            status_text = "변경" if item["changed"] else "유지"
            tag = "changed" if item["changed"] else "unchanged"
            if item["changed"]:
                changed_cnt += 1
            dirname = os.path.dirname(item["old_path"])
            self.rename_tree.insert("", "end", values=(
                status_text, item["old_name"], item["new_name"], dirname
            ), tags=(tag,))

        total = len(self.rename_files)
        self.rename_count_lbl.config(text=f"대상 파일: {total}개")
        self.rename_change_stat_lbl.config(text=f"변경 예정: {changed_cnt}개 / 유지: {total - changed_cnt}개")

    def _rename_run(self):
        if not self.rename_plan:
            messagebox.showwarning("안내", "변경할 대상 파일이 없습니다.")
            return

        changed_cnt = sum(1 for item in self.rename_plan if item["changed"])
        if changed_cnt == 0:
            messagebox.showinfo("안내", "변경될 파일명이 없습니다 (모두 기존 파일명과 동일).")
            return

        if not messagebox.askyesno("최종 확인", f"총 {changed_cnt}개의 파일명을 실제로 변경하시겠습니까?"):
            return

        plan_copy = list(self.rename_plan)
        success_cnt, err_cnt = hwp_core.execute_rename(plan_copy, log_fn=self.log)

        messagebox.showinfo("완료", f"파일명 변경 완료!\n- 성공: {success_cnt}개\n- 실패/스킵: {err_cnt}개")

        # 새 파일 경로로 목록 갱신
        new_file_list = []
        for item in plan_copy:
            if item["changed"] and os.path.exists(item["new_path"]):
                new_file_list.append(item["new_path"])
            elif os.path.exists(item["old_path"]):
                new_file_list.append(item["old_path"])
        self.rename_files = new_file_list
        self._rename_update_plan()

    # --------------------------------------------------------------------------
    # 하단 공통 진행 상태 및 로그 패널
    # --------------------------------------------------------------------------
    def _build_bottom_panel(self):
        bottom_frame = ttk.LabelFrame(self.root, text=" 작업 진행 상태 및 실시간 로그 ")
        bottom_frame.pack(fill=tk.BOTH, expand=False, padx=10, pady=6)

        # 프로그레스 바 & 상태 레이블 & 취소 버튼
        p_row = ttk.Frame(bottom_frame)
        p_row.pack(fill=tk.X, padx=8, pady=4)

        self.status_lbl = ttk.Label(p_row, text="준비 완료", font=("맑은 고딕", 9, "bold"))
        self.status_lbl.pack(side=tk.LEFT, padx=4)

        self.cancel_btn = ttk.Button(p_row, text="⏹ 작업 취소", style="Danger.TButton",
                                     command=self._cancel_task, state="disabled")
        self.cancel_btn.pack(side=tk.RIGHT, padx=4)

        ttk.Button(p_row, text="로그 지우기", style="Secondary.TButton",
                   command=self._clear_log).pack(side=tk.RIGHT, padx=4)

        self.progressbar = ttk.Progressbar(bottom_frame, mode="determinate")
        self.progressbar.pack(fill=tk.X, padx=8, pady=2)

        # 로그 스크롤 텍스트
        self.log_text = ScrolledText(bottom_frame, height=7, font=("Consolas", 9), wrap=tk.WORD, bg="#FAFAFA")
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        self.log("🚀 HWP Toolkit GUI가 성공적으로 실행되었습니다.")

    # --------------------------------------------------------------------------
    # 유틸리티 & 큐 제어
    # --------------------------------------------------------------------------
    def _tree_move_item(self, tree: ttk.Treeview, data_list: list, direction: int):
        """Treeview 항목 위/아래 순서 변경"""
        selected = tree.selection()
        if not selected:
            return
        idx = tree.index(selected[0])
        new_idx = idx + direction
        if 0 <= new_idx < len(data_list):
            item = data_list.pop(idx)
            data_list.insert(new_idx, item)
            if tree == self.merge_tree:
                self._merge_refresh_tree()
                new_sel = self.merge_tree.get_children()[new_idx]
                self.merge_tree.selection_set(new_sel)
            elif tree == self.prepend_tree:
                self._prepend_refresh_tree()
                new_sel = self.prepend_tree.get_children()[new_idx]
                self.prepend_tree.selection_set(new_sel)

    def log(self, message: str):
        now = datetime.now().strftime("%H:%M:%S")
        self.msg_queue.put(("log", f"[{now}] {message}"))

    def progress(self, current: int, total: int, status_text: str = ""):
        self.msg_queue.put(("progress", (current, total, status_text)))

    def _clear_log(self):
        self.log_text.delete("1.0", tk.END)

    def _start_task(self, title: str):
        self.is_running = True
        self.cancel_requested = False
        self.msg_queue.put(("task_start", title))

    def _finish_task(self):
        self.is_running = False
        self.msg_queue.put(("task_finish", None))

    def _cancel_task(self):
        if self.is_running:
            self.cancel_requested = True
            self.log("⚠️ 작업 취소 요청을 전송했습니다. 현재 단계 완료 후 안전하게 중단됩니다...")

    def _poll_queue(self):
        try:
            while True:
                msg_type, data = self.msg_queue.get_nowait()
                if msg_type == "log":
                    self.log_text.insert(tk.END, data + "\n")
                    self.log_text.see(tk.END)
                elif msg_type == "progress":
                    curr, total, status = data
                    if total > 0:
                        pct = int((curr / total) * 100)
                        self.progressbar["value"] = pct
                        self.status_lbl.config(text=f"처리 중: {pct}% ({status})")
                elif msg_type == "task_start":
                    self.status_lbl.config(text=f"진행 중: {data}...")
                    self.progressbar["value"] = 0
                    self.cancel_btn.config(state="normal")
                    self.merge_run_btn.config(state="disabled")
                    self.prepend_run_btn.config(state="disabled")
                    self.extract_run_btn.config(state="disabled")
                elif msg_type == "task_finish":
                    self.status_lbl.config(text="준비 완료")
                    self.cancel_btn.config(state="disabled")
                    self.merge_run_btn.config(state="normal")
                    self.prepend_run_btn.config(state="normal")
                    self.extract_run_btn.config(state="normal")
        except queue.Empty:
            pass

        self.root.after(100, self._poll_queue)


def main():
    root = tk.Tk()
    app = HwpToolkitApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
