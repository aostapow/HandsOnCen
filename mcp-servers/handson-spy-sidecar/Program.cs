using System.Text.Json;
using FlaUI.Core.AutomationElements;
using FlaUI.Core.Definitions;
using FlaUI.UIA3;

namespace HandsonSpySidecar;

static class Program
{
    [STAThread]
    static int Main()
    {
        Application.EnableVisualStyles();
        try
        {
            var line = Console.In.ReadLine();
            if (string.IsNullOrEmpty(line))
            {
                WriteError("empty request");
                return 1;
            }
            var req = JsonSerializer.Deserialize<Request>(line, new JsonSerializerOptions
            {
                PropertyNameCaseInsensitive = true,
            });
            if (req == null || string.IsNullOrEmpty(req.Command))
            {
                WriteError("invalid request");
                return 1;
            }
            var resp = Dispatch(req);
            Console.Out.WriteLine(JsonSerializer.Serialize(resp));
            return 0;
        }
        catch (Exception ex)
        {
            WriteError(ex.Message);
            return 1;
        }
    }

    static void WriteError(string msg) =>
        Console.Out.WriteLine(JsonSerializer.Serialize(new { error = msg }));

    static object Dispatch(Request req) => req.Command switch
    {
        "from_point" => FromPoint(req.Params),
        "inspect_full" => InspectFull(req.Params),
        "walk_tree" => WalkTree(req.Params),
        "highlight" => HighlightCmd(req.Params),
        "unhighlight" => HighlightOverlay.Unhighlight(),
        _ => new { error = $"unknown command: {req.Command}" },
    };

    static object HighlightCmd(JsonElement p)
    {
        int x = p.GetProperty("x").GetInt32();
        int y = p.GetProperty("y").GetInt32();
        int w = p.GetProperty("w").GetInt32();
        int h = p.GetProperty("h").GetInt32();
        int dur = p.TryGetProperty("duration_ms", out var d) ? d.GetInt32() : 3000;
        return HighlightOverlay.Highlight(x, y, w, h, dur);
    }

    static object FromPoint(JsonElement p)
    {
        using var automation = new UIA3Automation();
        int x = p.GetProperty("x").GetInt32();
        int y = p.GetProperty("y").GetInt32();
        var elem = automation.FromPoint(new Point(x, y));
        if (elem == null) return new { found = false, error = "no element" };
        return new { found = true, properties = InspectElement(elem) };
    }

    static object InspectFull(JsonElement p)
    {
        using var automation = new UIA3Automation();
        var window = ResolveWindow(automation, GetStr(p, "window_title"));
        if (window == null) return new { found = false, error = "no window" };
        var name = GetStr(p, "name");
        var aid = GetStr(p, "automation_id");
        AutomationElement? elem = null;
        if (!string.IsNullOrEmpty(aid))
            elem = window.FindFirstDescendant(cf => cf.ByAutomationId(aid));
        if (elem == null && !string.IsNullOrEmpty(name))
            elem = window.FindFirstDescendant(cf => cf.ByName(name));
        if (elem == null) return new { found = false, error = "not found" };
        return new { found = true, properties = InspectElement(elem) };
    }

    static object WalkTree(JsonElement p)
    {
        using var automation = new UIA3Automation();
        var window = ResolveWindow(automation, GetStr(p, "window_title"));
        if (window == null) return new { elements = Array.Empty<object>() };
        int maxDepth = p.TryGetProperty("max_depth", out var dp) ? dp.GetInt32() : 5;
        bool visibleOnly = p.TryGetProperty("visible_only", out var vp) && vp.GetBoolean();
        string roleFilter = GetStr(p, "role");

        var elements = new List<Dictionary<string, object?>>();
        WalkElement(window, 0, maxDepth, visibleOnly, roleFilter, elements);
        return new { elements, count = elements.Count };
    }

    static void WalkElement(
        AutomationElement e,
        int depth,
        int maxDepth,
        bool visibleOnly,
        string roleFilter,
        List<Dictionary<string, object?>> outList)
    {
        if (depth > maxDepth || outList.Count >= 500) return;
        Dictionary<string, object?>? info = null;
        try
        {
            info = InspectElement(e);
        }
        catch
        {
            if (depth >= maxDepth) return;
            goto walk_children;
        }

        if (visibleOnly && e.IsOffscreen) { /* skip self but may walk children */ }
        else
        {
            var role = info["role"]?.ToString() ?? "";
            if (string.IsNullOrEmpty(roleFilter) || role.Contains(roleFilter, StringComparison.OrdinalIgnoreCase))
            {
                if (!visibleOnly || !(info["is_offscreen"] as bool? ?? false))
                    if (!string.IsNullOrEmpty(info["name"]?.ToString()) || role != "Pane")
                        outList.Add(info);
            }
        }
        if (depth >= maxDepth) return;

        walk_children:
        try
        {
            foreach (var child in e.FindAllChildren())
                WalkElement(child, depth + 1, maxDepth, visibleOnly, roleFilter, outList);
        }
        catch { /* skip broken subtree */ }
    }

    static Dictionary<string, object?> InspectElement(AutomationElement e)
    {
        var r = e.BoundingRectangle;
        var patterns = new Dictionary<string, object?>();
        try
        {
            if (e.Patterns.Invoke.IsSupported) patterns["Invoke"] = new { supported = true };
            if (e.Patterns.Value.IsSupported)
            {
                try { patterns["Value"] = new { supported = true, value = e.Patterns.Value.Pattern.Value.Value }; }
                catch { patterns["Value"] = new { supported = true }; }
            }
            if (e.Patterns.Toggle.IsSupported)
            {
                try { patterns["Toggle"] = new { supported = true, state = e.Patterns.Toggle.Pattern.ToggleState.ToString() }; }
                catch { patterns["Toggle"] = new { supported = true }; }
            }
            if (e.Patterns.ExpandCollapse.IsSupported)
            {
                try { patterns["ExpandCollapse"] = new { supported = true, state = e.Patterns.ExpandCollapse.Pattern.ExpandCollapseState.ToString() }; }
                catch { patterns["ExpandCollapse"] = new { supported = true }; }
            }
            if (e.Patterns.LegacyIAccessible.IsSupported) patterns["LegacyIAccessible"] = new { supported = true };
        }
        catch { /* patterns optional */ }

        string automationId = "";
        try { automationId = e.AutomationId ?? ""; } catch { }

        long hwnd = 0;
        try { hwnd = (long)e.Properties.NativeWindowHandle.ValueOrDefault; } catch { }

        return new Dictionary<string, object?>
        {
            ["name"] = SafeString(() => e.Name ?? ""),
            ["role"] = SafeString(() => e.ControlType.ToString()),
            ["localized_control_type"] = SafeString(() => e.Properties.LocalizedControlType.ValueOrDefault ?? ""),
            ["x"] = (int)r.X,
            ["y"] = (int)r.Y,
            ["width"] = (int)r.Width,
            ["height"] = (int)r.Height,
            ["automation_id"] = automationId,
            ["class_name"] = SafeString(() => e.ClassName ?? ""),
            ["framework_id"] = SafeString(() => e.Properties.FrameworkId.ValueOrDefault ?? ""),
            ["process_id"] = SafeInt(() => e.Properties.ProcessId.ValueOrDefault),
            ["native_window_handle"] = hwnd,
            ["access_key"] = SafeString(() => e.Properties.AccessKey.ValueOrDefault ?? ""),
            ["accelerator_key"] = SafeString(() => e.Properties.AcceleratorKey.ValueOrDefault ?? ""),
            ["help_text"] = SafeString(() => e.Properties.HelpText.ValueOrDefault ?? ""),
            ["item_status"] = SafeString(() => e.Properties.ItemStatus.ValueOrDefault ?? ""),
            ["item_type"] = SafeString(() => e.Properties.ItemType.ValueOrDefault ?? ""),
            ["aria_role"] = SafeString(() => e.Properties.AriaRole.ValueOrDefault ?? ""),
            ["aria_properties"] = SafeString(() => e.Properties.AriaProperties.ValueOrDefault ?? ""),
            ["is_enabled"] = SafeBool(() => e.IsEnabled),
            ["is_offscreen"] = SafeBool(() => e.IsOffscreen),
            ["has_keyboard_focus"] = SafeBool(() => e.Properties.HasKeyboardFocus.ValueOrDefault),
            ["is_keyboard_focusable"] = SafeBool(() => e.Properties.IsKeyboardFocusable.ValueOrDefault),
            ["is_password"] = SafeBool(() => e.Properties.IsPassword.ValueOrDefault),
            ["is_content_element"] = SafeBool(() => e.Properties.IsContentElement.ValueOrDefault),
            ["is_control_element"] = SafeBool(() => e.Properties.IsControlElement.ValueOrDefault),
            ["patterns"] = patterns,
        };
    }

    static string SafeString(Func<string> getter)
    {
        try { return getter(); }
        catch { return ""; }
    }

    static int SafeInt(Func<int> getter)
    {
        try { return getter(); }
        catch { return 0; }
    }

    static bool SafeBool(Func<bool> getter)
    {
        try { return getter(); }
        catch { return false; }
    }

    static AutomationElement? ResolveWindow(UIA3Automation automation, string title)
    {
        var desktop = automation.GetDesktop();
        if (string.IsNullOrEmpty(title))
        {
            var fg = automation.FocusedElement();
            if (fg != null)
            {
                var w = fg.AsWindow();
                if (w != null) return w;
                return fg;
            }
            return desktop.FindFirstDescendant(cf => cf.ByControlType(ControlType.Window));
        }

        // Partial title match (case-insensitive), consistent with Python find_matching_window.
        foreach (var window in desktop.FindAllDescendants(cf => cf.ByControlType(ControlType.Window)))
        {
            var name = window.Name ?? "";
            if (name.Contains(title, StringComparison.OrdinalIgnoreCase))
                return window;
        }
        return null;
    }

    static string GetStr(JsonElement p, string key) =>
        p.TryGetProperty(key, out var v) ? v.GetString() ?? "" : "";
}

class Request
{
    public string Command { get; set; } = "";
    public JsonElement Params { get; set; }
}
