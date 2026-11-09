package com.mohd.fallingsticks;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.view.DisplayCutout;
import android.view.View;
import android.view.WindowInsets;
import android.view.WindowInsetsController;
import android.view.WindowManager;
import android.webkit.RenderProcessGoneDetail;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.window.OnBackInvokedCallback;
import android.window.OnBackInvokedDispatcher;

import com.google.android.gms.tasks.OnCompleteListener;
import com.google.android.gms.tasks.Task;
import com.google.android.play.core.review.ReviewInfo;
import com.google.android.play.core.review.ReviewManager;
import com.google.android.play.core.review.ReviewManagerFactory;

import java.io.InputStream;

/**
 * Falling Sticks runs fully offline: the game files live in the APK (assets/www) and are served to the WebView
 * from https://appassets.androidplatform.net/, so storage, audio and fonts behave like on the web.
 */
public class MainActivity extends Activity {
    private static final String HOST = "appassets.androidplatform.net";
    private static final int BG = Color.rgb(7, 11, 22);
    private WebView web;
    private OnBackInvokedCallback backCb;
    /** WebView has no navigator.share: the game's challenge sharing goes to the Android share sheet instead. */
    private static final String SHARE_SHIM = "if(!navigator.share&&window.FSNative){navigator.share=function(d){d=d||{};"
            + "FSNative.share(String(d.title||''),[d.text,d.url].filter(Boolean).join('\\n'));return Promise.resolve();};}";

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

        web = new WebView(this);
        web.setBackgroundColor(BG);
        web.setOverScrollMode(View.OVER_SCROLL_NEVER);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(false);
        s.setTextZoom(100);
        s.setSupportZoom(false);
        web.setWebChromeClient(new WebChromeClient());
        web.setWebViewClient(new WebViewClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest req) {
                Uri u = req.getUrl();
                if (!HOST.equals(u.getHost())) return null;
                String path = u.getPath();
                if (path == null || path.equals("/")) path = "/index.html";
                try {
                    InputStream in = getAssets().open("www" + path);
                    return new WebResourceResponse(mime(path), mime(path).startsWith("text") ? "utf-8" : null, in);
                } catch (Exception e) {
                    return new WebResourceResponse("text/plain", "utf-8", 404, "Not Found", null, null);
                }
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest req) {
                Uri u = req.getUrl();
                if (HOST.equals(u.getHost())) return false;
                String sc = u.getScheme();
                if ("https".equals(sc) || "http".equals(sc) || "mailto".equals(sc)) {   // outside links open in the browser; nothing else
                    try { startActivity(new Intent(Intent.ACTION_VIEW, u)); } catch (Exception ignored) { }
                }
                return true;
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                if (url != null && url.contains(HOST)) view.evaluateJavascript(SHARE_SHIM, null);
            }

            /** If the WebView's renderer dies (low memory), start over instead of letting the whole app crash. */
            @Override
            public boolean onRenderProcessGone(WebView view, RenderProcessGoneDetail detail) {
                if (view == web) {
                    ((FrameLayout) view.getParent()).removeView(view);
                    view.destroy();
                    web = null;
                    recreate();
                }
                return true;
            }
        });

        web.addJavascriptInterface(new Bridge(), "FSNative");   // only our own bundled pages are ever loaded in this WebView

        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(BG);
        root.addView(web, new FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));
        root.setOnApplyWindowInsetsListener(new View.OnApplyWindowInsetsListener() {   // keep the game clear of the camera cut-out
            @Override
            @SuppressWarnings("deprecation")
            public WindowInsets onApplyWindowInsets(View v, WindowInsets insets) {
                if (Build.VERSION.SDK_INT >= 28) {
                    DisplayCutout c = insets.getDisplayCutout();
                    if (c != null) v.setPadding(c.getSafeInsetLeft(), c.getSafeInsetTop(), c.getSafeInsetRight(), c.getSafeInsetBottom());
                    else v.setPadding(0, 0, 0, 0);
                    return insets.consumeDisplayCutout();   // the padding already clears it; the page's env(safe-area-inset-*) must not add it again
                }
                return insets;
            }
        });
        setContentView(root);
        hideSystemBars();

        if (Build.VERSION.SDK_INT >= 33 && backCb == null) {   // Android 13+ back (predictive back; Android 16 no longer calls onBackPressed)
            backCb = new OnBackInvokedCallback() { @Override public void onBackInvoked() { goBack(); } };
            getOnBackInvokedDispatcher().registerOnBackInvokedCallback(OnBackInvokedDispatcher.PRIORITY_DEFAULT, backCb);
        }

        if (state != null) web.restoreState(state);
        else web.loadUrl("https://" + HOST + "/index.html?app=android");
    }

    /** Called from the game (window.FSNative). */
    private class Bridge {
        @JavascriptInterface
        public void review() { runOnUiThread(new Runnable() { @Override public void run() { askReview(); } }); }

        /** navigator.share replacement: the system share sheet with the challenge text + link. */
        @JavascriptInterface
        public void share(final String title, final String text) {
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    try {
                        Intent i = new Intent(Intent.ACTION_SEND).setType("text/plain").putExtra(Intent.EXTRA_TEXT, text);
                        if (title != null && title.length() > 0) i.putExtra(Intent.EXTRA_SUBJECT, title);
                        startActivity(Intent.createChooser(i, title));
                    } catch (Exception ignored) { }
                }
            });
        }
    }

    /** Google Play In-App Review: Play decides whether the card really shows (quota); it does nothing outside a Play install. */
    private void askReview() {
        try {
            final ReviewManager m = ReviewManagerFactory.create(this);
            m.requestReviewFlow().addOnCompleteListener(new OnCompleteListener<ReviewInfo>() {
                @Override
                public void onComplete(Task<ReviewInfo> task) {
                    if (task.isSuccessful() && !isFinishing()) m.launchReviewFlow(MainActivity.this, task.getResult());
                }
            });
        } catch (Exception ignored) { }
    }

    private static String mime(String p) {
        String f = p.toLowerCase();
        if (f.endsWith(".html")) return "text/html";
        if (f.endsWith(".js")) return "text/javascript";
        if (f.endsWith(".css")) return "text/css";
        if (f.endsWith(".json") || f.endsWith(".webmanifest")) return "application/json";
        if (f.endsWith(".png")) return "image/png";
        if (f.endsWith(".svg")) return "image/svg+xml";
        if (f.endsWith(".woff2")) return "font/woff2";
        if (f.endsWith(".txt")) return "text/plain";
        return "application/octet-stream";
    }

    @SuppressWarnings("deprecation")
    private void hideSystemBars() {
        if (Build.VERSION.SDK_INT >= 30) {
            getWindow().setDecorFitsSystemWindows(false);
            WindowInsetsController c = getWindow().getInsetsController();
            if (c != null) {
                c.hide(WindowInsets.Type.statusBars() | WindowInsets.Type.navigationBars());
                c.setSystemBarsBehavior(WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);
            }
        } else {
            getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY | View.SYSTEM_UI_FLAG_FULLSCREEN
                    | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION | View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                    | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN);
        }
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) hideSystemBars();
    }

    /** Android 12 and older (13+ uses backCb). */
    @Override
    @SuppressWarnings("deprecation")
    public void onBackPressed() { goBack(); }

    /** The back button goes through the game (close a dialog, pause, step back); it leaves only from the main menu. */
    private void goBack() {
        if (web == null) { finish(); return; }
        web.evaluateJavascript("window.appBack ? appBack() : 'exit'", new ValueCallback<String>() {
            @Override
            public void onReceiveValue(String v) { if (v == null || v.equals("null") || v.contains("exit")) finish(); }   // "null" = the page failed: don't trap the player
        });
    }

    @Override
    protected void onPause() {
        if (web != null) { web.onPause(); web.pauseTimers(); }
        super.onPause();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (web != null) { web.resumeTimers(); web.onResume(); }
        hideSystemBars();
    }

    @Override
    protected void onSaveInstanceState(Bundle out) {
        super.onSaveInstanceState(out);
        if (web != null) web.saveState(out);
    }

    @Override
    protected void onDestroy() {
        if (backCb != null && Build.VERSION.SDK_INT >= 33) getOnBackInvokedDispatcher().unregisterOnBackInvokedCallback(backCb);
        if (web != null) web.destroy();
        super.onDestroy();
    }
}
