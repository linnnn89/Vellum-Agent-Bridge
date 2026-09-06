using System.Globalization;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Xml.Linq;

namespace WpfCanary;

internal static class Program
{
    [STAThread]
    private static int Main(string[] args)
    {
        if (args.Length == 2 && args[0] == "--security")
        {
            return CheckSecurity(args[1]);
        }
        if (args.Length == 2 && args[0] == "--image")
        {
            var doc = XDocument.Parse(File.ReadAllText(args[1]));
            XNamespace x = "http://schemas.microsoft.com/winfx/2006/xaml";
            doc.Root!.Attribute(x + "Class")!.Remove();
            var context = new System.Windows.Markup.ParserContext { BaseUri = new Uri(Path.GetFullPath(args[1])) };
            var window = (Window)System.Windows.Markup.XamlReader.Parse(doc.ToString(), context);
            var bitmap = (System.Windows.Media.Imaging.BitmapSource)((Image)window.Content).Source;
            if (bitmap.PixelWidth != 1 || bitmap.PixelHeight != 1)
                throw new InvalidOperationException("Image did not decode");
            Console.WriteLine("IMAGE_OK");
            return 0;
        }
        if (args.Length < 3)
        {
            Console.Error.WriteLine("Usage: WpfCanary <MainWindow.xaml> <width1> <width2>");
            return 2;
        }

        var xamlPath = args[0];
        var width1 = double.Parse(args[1], CultureInfo.InvariantCulture);
        var width2 = double.Parse(args[2], CultureInfo.InvariantCulture);
        var tracks = ReadColumnTracks(File.ReadAllText(xamlPath));
        if (tracks.Count == 0)
        {
            Console.Error.WriteLine("No Grid.ColumnDefinitions found.");
            return 1;
        }

        var a = Measure(tracks, width1);
        var b = Measure(tracks, width2);
        var delta = a.Zip(b, (left, right) => right - left).ToArray();

        Console.WriteLine($"{Fmt(width1)}={Join(a)};{Fmt(width2)}={Join(b)};delta={Join(delta)}");
        return 0;
    }

    private static int CheckSecurity(string path)
    {
        var doc = XDocument.Parse(File.ReadAllText(path));
        XNamespace x = "http://schemas.microsoft.com/winfx/2006/xaml";
        doc.Root!.Attribute(x + "Class")!.Remove();
        var window = (Window)System.Windows.Markup.XamlReader.Parse(doc.ToString());
        const string literal = "{Binding Steal}";
        var panel = (Panel)window.Content;
        var button = (Button)panel.Children[0];
        var input = (TextBox)panel.Children[1];
        var text = (TextBlock)panel.Children[2];
        if (window.Title != literal || (string)button.Content != literal ||
            (string)button.ToolTip != literal ||
            System.Windows.Automation.AutomationProperties.GetName(button) != literal ||
            System.Windows.Automation.AutomationProperties.GetHelpText(button) != literal ||
            input.Text != literal || (string)input.ToolTip != literal ||
            (string)input.Tag != literal || text.Text != literal || text.FontFamily.Source != literal ||
            System.Windows.Data.BindingOperations.IsDataBound(button, Button.ContentProperty) ||
            System.Windows.Data.BindingOperations.IsDataBound(input, TextBox.TextProperty) ||
            ((System.Windows.Media.SolidColorBrush)text.Foreground).Color.ToString() != "#80123456")
        {
            throw new InvalidOperationException("Literal or ARGB interpretation changed");
        }
        Console.WriteLine("SECURITY_OK");
        return 0;
    }

    private static List<GridLength> ReadColumnTracks(string xaml)
    {
        var doc = XDocument.Parse(xaml);
        XNamespace ns = "http://schemas.microsoft.com/winfx/2006/xaml/presentation";
        var defs = doc.Descendants(ns + "Grid.ColumnDefinitions").FirstOrDefault();
        if (defs is null)
        {
            return [];
        }

        return defs.Elements(ns + "ColumnDefinition")
            .Select(el => ParseGridLength(el.Attribute("Width")?.Value ?? "*"))
            .ToList();
    }

    private static GridLength ParseGridLength(string raw)
    {
        raw = raw.Trim();
        if (raw.Equals("Auto", StringComparison.OrdinalIgnoreCase))
        {
            return GridLength.Auto;
        }

        if (raw.EndsWith("*", StringComparison.Ordinal))
        {
            var weight = raw.Length == 1 ? 1.0 : double.Parse(raw[..^1], CultureInfo.InvariantCulture);
            return new GridLength(weight, GridUnitType.Star);
        }

        return new GridLength(double.Parse(raw, CultureInfo.InvariantCulture), GridUnitType.Pixel);
    }

    private static double[] Measure(List<GridLength> tracks, double width)
    {
        var grid = new Grid { Width = width, Height = 400 };
        foreach (var track in tracks)
        {
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = track });
        }

        for (var i = 0; i < tracks.Count; i++)
        {
            var border = new Border();
            Grid.SetColumn(border, i);
            grid.Children.Add(border);
        }

        grid.Measure(new Size(width, 400));
        grid.Arrange(new Rect(0, 0, width, 400));
        return grid.ColumnDefinitions.Select(c => c.ActualWidth).ToArray();
    }

    private static string Join(IEnumerable<double> values) =>
        string.Join(",", values.Select(Fmt));

    private static string Fmt(double value) =>
        value.ToString("0.###", CultureInfo.InvariantCulture);
}
