using System.Text.Json;
using FlaUI.Core;
using FlaUI.Core.AutomationElements;
using FlaUI.Core.Definitions;
using FlaUI.UIA3;

namespace HandsonUiaSidecar;

static class Program
{
    static int Main()
    {
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

    static object Dispatch(Request req)
    {
        using var automation = new UIA3Automation();
        return req.Command switch
        {
            "from_point" => FromPoint(automation, req.Params),
            "find" => Find(automation, req.Params),
            "list_tree" => ListTree(automation, req.Params),
            "get_properties" => GetProperties(automation, req.Params),
            "invoke" => Invoke(automation, req.Params),
            "set_value" => SetValue(automation, req.Params),
            _ => new { error = $"unknown command: {req.Command}" },
        };
    }

    static AutomationElement? ResolveWindow(UIA3Automation automation, string title)
    {
        var desktop = automation.GetDesktop();
        if (string.IsNullOrEmpty(title))
        {
            var fg = automation.FocusedElement();
            if (fg != null) return fg;
            return desktop.FindFirstDescendant(cf => cf.ByControlType(ControlType.Window));
        }
        return desktop.FindFirstDescendant(cf =>
            cf.ByControlType(ControlType.Window).And(cf.ByName(title, FlaUI.Core.Definitions.PropertyConditionFlags.IgnoreCase)));
    }

    static Dictionary<string, object?> ElemToDict(AutomationElement e)
    {
        var r = e.BoundingRectangle;
        var patterns = new List<string>();
        if (e.Patterns.Invoke.IsSupported) patterns.Add("Invoke");
        if (e.Patterns.Value.IsSupported) patterns.Add("Value");
        if (e.Patterns.Toggle.IsSupported) patterns.Add("Toggle");
        if (e.Patterns.ExpandCollapse.IsSupported) patterns.Add("ExpandCollapse");
        if (e.Patterns.Scroll.IsSupported) patterns.Add("Scroll");
        if (e.Patterns.LegacyIAccessible.IsSupported) patterns.Add("LegacyIAccessible");

        return new Dictionary<string, object?>
        {
            ["name"] = e.Name ?? "",
            ["role"] = e.ControlType.ToString(),
            ["x"] = (int)r.X,
            ["y"] = (int)r.Y,
            ["width"] = (int)r.Width,
            ["height"] = (int)r.Height,
            ["value"] = e.Properties.Name.ValueOrDefault ?? "",
            ["automation_id"] = e.AutomationId ?? "",
            ["class_name"] = e.ClassName ?? "",
            ["framework_id"] = e.Properties.FrameworkId.ValueOrDefault ?? "",
            ["enabled"] = e.IsEnabled,
            ["visible"] = !e.IsOffscreen,
            ["patterns"] = patterns,
        };
    }

    static object FromPoint(UIA3Automation automation, JsonElement p)
    {
        int x = p.GetProperty("x").GetInt32();
        int y = p.GetProperty("y").GetInt32();
        var elem = automation.FromPoint(new System.Drawing.Point(x, y));
        if (elem == null) return new { error = "no element" };
        return new { element = ElemToDict(elem) };
    }

    static object Find(UIA3Automation automation, JsonElement p)
    {
        var window = ResolveWindow(automation, GetStr(p, "window_title"));
        if (window == null) return new { elements = Array.Empty<object>() };
        var name = GetStr(p, "name");
        var role = GetStr(p, "role");
        var aid = GetStr(p, "automation_id");
        var all = window.FindAllDescendants();
        var matches = all.Where(e =>
            (string.IsNullOrEmpty(name) || (e.Name ?? "").Contains(name, StringComparison.OrdinalIgnoreCase)) &&
            (string.IsNullOrEmpty(role) || e.ControlType.ToString().Equals(role, StringComparison.OrdinalIgnoreCase)) &&
            (string.IsNullOrEmpty(aid) || (e.AutomationId ?? "") == aid)
        ).Select(ElemToDict).ToList();
        int index = p.TryGetProperty("index", out var ip) ? ip.GetInt32() : 0;
        if (index > 0 && matches.Count > index)
            matches = new List<Dictionary<string, object?>> { matches[index] };
        return new { elements = matches };
    }

    static object ListTree(UIA3Automation automation, JsonElement p)
    {
        var window = ResolveWindow(automation, GetStr(p, "window_title"));
        if (window == null) return new { elements = Array.Empty<object>() };
        int maxDepth = p.TryGetProperty("max_depth", out var dp) ? dp.GetInt32() : 5;
        var role = GetStr(p, "role");
        var all = window.FindAllDescendants();
        var elements = all
            .Where(e => string.IsNullOrEmpty(role) || e.ControlType.ToString().Equals(role, StringComparison.OrdinalIgnoreCase))
            .Where(e => !string.IsNullOrEmpty(e.Name) || e.ControlType != ControlType.Pane)
            .Take(500)
            .Select(ElemToDict)
            .ToList();
        return new { elements };
    }

    static object GetProperties(UIA3Automation automation, JsonElement p)
    {
        var result = Find(automation, p);
        var json = JsonSerializer.Serialize(result);
        using var doc = JsonDocument.Parse(json);
        var elements = doc.RootElement.GetProperty("elements");
        if (elements.GetArrayLength() == 0)
            return new { error = "not found" };
        return new { properties = JsonSerializer.Deserialize<object>(elements[0].GetRawText()) };
    }

    static object Invoke(UIA3Automation automation, JsonElement p)
    {
        var result = Find(automation, p);
        var window = ResolveWindow(automation, GetStr(p, "window_title"));
        if (window == null) return new { success = false, error = "no window" };
        var name = GetStr(p, "name");
        var elem = window.FindFirstDescendant(cf => cf.ByName(name));
        if (elem == null) return new { success = false, error = "not found" };
        elem.Patterns.Invoke.Pattern.Invoke();
        return new { success = true };
    }

    static object SetValue(UIA3Automation automation, JsonElement p)
    {
        var window = ResolveWindow(automation, GetStr(p, "window_title"));
        if (window == null) return new { success = false, error = "no window" };
        var name = GetStr(p, "name");
        var value = GetStr(p, "value");
        var elem = window.FindFirstDescendant(cf => cf.ByName(name));
        if (elem == null) return new { success = false, error = "not found" };
        elem.Patterns.Value.Pattern.SetValue(value);
        return new { success = true };
    }

    static string GetStr(JsonElement p, string key) =>
        p.TryGetProperty(key, out var v) ? v.GetString() ?? "" : "";
}

class Request
{
    public string Command { get; set; } = "";
    public JsonElement Params { get; set; }
}
