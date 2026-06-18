using System.Drawing;
using System.Windows.Forms;

namespace HandsonSpySidecar;

/// <summary>Automation Spy-style red border overlay (4 topmost bars).</summary>
static class HighlightOverlay
{
    const int Thickness = 3;
    static Form? _top, _left, _bottom, _right;
    static System.Threading.Timer? _timer;

    static Form MakeBar(string name)
    {
        var f = new Form
        {
            Name = name,
            FormBorderStyle = FormBorderStyle.None,
            StartPosition = FormStartPosition.Manual,
            ShowInTaskbar = false,
            TopMost = true,
            BackColor = Color.Red,
            Opacity = 0.85,
        };
        f.Show();
        return f;
    }

    public static object Highlight(int x, int y, int w, int h, int durationMs)
    {
        Unhighlight();
        _top = MakeBar("spy_top");
        _left = MakeBar("spy_left");
        _bottom = MakeBar("spy_bottom");
        _right = MakeBar("spy_right");

        _top.Location = new Point(x, y);
        _top.Size = new Size(w + 2 * Thickness, Thickness);

        _left.Location = new Point(x, y);
        _left.Size = new Size(Thickness, h + 2 * Thickness);

        _bottom.Location = new Point(x, y + h + Thickness);
        _bottom.Size = new Size(w + 2 * Thickness, Thickness);

        _right.Location = new Point(x + w + Thickness, y);
        _right.Size = new Size(Thickness, h + 2 * Thickness);

        if (durationMs > 0)
        {
            _timer = new System.Threading.Timer(_ => Unhighlight(), null, durationMs, Timeout.Infinite);
        }
        return new { success = true, x, y, w, h, duration_ms = durationMs };
    }

    public static object Unhighlight()
    {
        _timer?.Dispose();
        _timer = null;
        foreach (var f in new[] { _top, _left, _bottom, _right })
        {
            if (f != null)
            {
                try { f.Close(); f.Dispose(); } catch { }
            }
        }
        _top = _left = _bottom = _right = null;
        return new { success = true };
    }
}
