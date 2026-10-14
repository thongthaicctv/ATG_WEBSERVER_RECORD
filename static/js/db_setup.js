// static/js/db_setup.js
// WEB-DB-FIRST-RUN-SETUP: Test ket noi (SELECT 1) + Luu Database qua fetch.
(function () {
    function showResult(box, ok, message) {
        if (!box) {
            return;
        }
        box.textContent = message || (ok ? "OK" : "Lỗi");
        box.className = ok ? "alert-success" : "alert-error";
        box.hidden = false;
    }

    function bindForm(form) {
        var box = form.querySelector("[data-db-result]");
        var testBtn = form.querySelector("[data-db-test]");
        var saveBtn = form.querySelector("[data-db-save]");
        var busy = false;

        function post(url, btn, busyText) {
            if (busy || !url) {
                return;
            }
            busy = true;
            var oldText = btn ? btn.textContent : "";
            if (testBtn) { testBtn.disabled = true; }
            if (saveBtn) { saveBtn.disabled = true; }
            if (btn) { btn.textContent = busyText; }

            fetch(url, {
                method: "POST",
                body: new FormData(form),
                credentials: "same-origin",
                headers: { "X-Requested-With": "fetch" }
            })
                .then(function (resp) {
                    return resp.json().catch(function () {
                        return { ok: false, message: "Phản hồi không hợp lệ từ WebServer (HTTP " + resp.status + "). Có thể phiên đăng nhập đã hết hạn." };
                    });
                })
                .then(function (data) {
                    showResult(box, !!data.ok, data.message);
                    if (data.ok && data.password_saved) {
                        var pwd = form.querySelector("[name=db_password]");
                        if (pwd) {
                            pwd.value = "";
                            pwd.placeholder = "Đã lưu mật khẩu — để trống để giữ nguyên";
                        }
                    }
                    if (data.ok && data.redirect) {
                        setTimeout(function () { window.location.href = data.redirect; }, 1200);
                    }
                })
                .catch(function (err) {
                    showResult(box, false, "Không gửi được yêu cầu tới WebServer: " + err);
                })
                .then(function () {
                    busy = false;
                    if (testBtn) { testBtn.disabled = false; }
                    if (saveBtn) { saveBtn.disabled = false; }
                    if (btn) { btn.textContent = oldText; }
                });
        }

        if (testBtn) {
            testBtn.addEventListener("click", function (e) {
                e.preventDefault();
                post(form.getAttribute("data-test-url"), testBtn, "Đang kiểm tra...");
            });
        }

        form.addEventListener("submit", function (e) {
            e.preventDefault();
            post(form.getAttribute("data-save-url"), saveBtn, "Đang lưu...");
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        var forms = document.querySelectorAll("form[data-db-form]");
        for (var i = 0; i < forms.length; i++) {
            bindForm(forms[i]);
        }
    });
})();
