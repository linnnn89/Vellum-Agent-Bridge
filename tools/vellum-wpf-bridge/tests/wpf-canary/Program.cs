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
