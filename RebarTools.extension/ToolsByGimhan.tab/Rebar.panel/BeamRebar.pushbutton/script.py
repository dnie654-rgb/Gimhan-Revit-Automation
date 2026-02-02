# -*- coding: utf-8 -*-
__title__ = 'Beam Rebar'
__doc__ = 'Parametric rebar editor with auto-spacing for multi-layer support.'

from pyrevit import revit, DB, forms, script
import os
import clr
import math
import json
import traceback

clr.AddReference('PresentationCore')
clr.AddReference('PresentationFramework')
clr.AddReference('WindowsBase')
from System.Windows import Window, Point, UIElement
from System.Windows.Controls import Canvas, ToolTip, ComboBox
from System.Windows.Shapes import Rectangle, Ellipse
from System.Windows.Media import Brushes, Color, SolidColorBrush
from System.Collections.Generic import List

# --- Constants ---
FRAMING_CAT_ID = int(DB.BuiltInCategory.OST_StructuralFraming)

# --- Selection Filter ---
from Autodesk.Revit.UI.Selection import ISelectionFilter
class BeamSelectionFilter(ISelectionFilter):
    def AllowElement(self, elem):
        try:
            if elem.Category and elem.Category.Id.IntegerValue == FRAMING_CAT_ID:
                return True
        except: pass
        return False
    def AllowReference(self, ref, pt): return True

# --- Helper Classes ---
class RebarPoint:
    def __init__(self, lx, ly, diameter_ft, bar_type_name):
        self.lx, self.ly = lx, ly 
        self.diameter_ft = diameter_ft
        self.type_name = bar_type_name

class ProfileManager:
    def __init__(self):
        self.file_path = os.path.join(os.path.dirname(__file__), "profiles.json")
        self.profiles = {}
        self.load_profiles()

    def load_profiles(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r') as f:
                    self.profiles = json.load(f)
            except: self.profiles = {}
        
        if "Default" not in self.profiles:
            self.profiles["Default"] = {
                "End Sections": {"T1": 2, "T2": 0, "B1": 2, "B2": 0},
                "Middle Section": {"T1": 2, "T2": 0, "B1": 2, "B2": 0},
                "Global": {
                    "SideCover": 25, "EndOffset": 40, "EndSpacing": 150, "MidSpacing": 250,
                    "BeamWidth": 300, "BeamHeight": 600
                }
            }

    def save_profile(self, name, data):
        self.profiles[name] = data
        try:
            with open(self.file_path, 'w') as f:
                json.dump(self.profiles, f, indent=2)
            return True
        except: return False

class ParametricRebarWindow(forms.WPFWindow):
    def __init__(self, xaml_file):
        super(ParametricRebarWindow, self).__init__(xaml_file)
        self.beam_w_ft = 1.0 
        self.beam_h_ft = 2.0
        self.bar_types_data = [] 
        self.stirrup_types_data = []
        self.pm = None
        self.zone_configs = {
            "End Sections": {"T1": 2, "T2": 0, "B1": 2, "B2": 0},
            "Middle Section": {"T1": 2, "T2": 0, "B1": 2, "B2": 0}
        }
        self.current_zone = "End Sections"
        self.bars = {"End Sections": [], "Middle Section": []}

    def setup_data(self, bar_types_data, stirrup_types_data, profile_manager):
        self.bar_types_data = bar_types_data
        self.stirrup_types_data = stirrup_types_data
        self.pm = profile_manager
        
        self.populate_combos()
        
        # Events
        self.bar_type_selector.SelectionChanged += self.global_input_changed
        self.stirrup_selector.SelectionChanged += self.global_input_changed
        self.side_cover.TextChanged += self.global_input_changed
        self.end_offset.TextChanged += self.global_input_changed
        self.end_spacing.TextChanged += self.global_input_changed
        self.mid_spacing.TextChanged += self.global_input_changed
        self.beam_width_ui.TextChanged += self.global_input_changed
        self.beam_height_ui.TextChanged += self.global_input_changed
        
        self.profile_selector.SelectionChanged += self.profile_changed
        self.save_profile_btn.Click += self.save_profile_click
        
        for cb in [self.top_L1_qty, self.top_L2_qty, self.bot_L1_qty, self.bot_L2_qty]:
            cb.SelectionChanged += self.zone_input_changed
            
        self.update_zoning_info()
        self.load_initial_profile()
        self.calculate_all_zones()

    def populate_combos(self):
        for cb in [self.top_L1_qty, self.top_L2_qty, self.bot_L1_qty, self.bot_L2_qty]:
            cb.Items.Clear()
            for i in range(11): cb.Items.Add(str(i))
            cb.SelectedIndex = 0

        self.profile_selector.Items.Clear()
        for p_name in sorted(self.pm.profiles.keys()): self.profile_selector.Items.Add(p_name)
        
        self.bar_type_selector.Items.Clear()
        for data in self.bar_types_data: self.bar_type_selector.Items.Add(data[0])
        if self.bar_type_selector.Items.Count > 0: self.bar_type_selector.SelectedIndex = 0
        
        self.stirrup_selector.Items.Clear()
        for data in self.stirrup_types_data: self.stirrup_selector.Items.Add(data[0])
        if self.stirrup_selector.Items.Count > 0: self.stirrup_selector.SelectedIndex = 0

    def load_initial_profile(self):
        idx = self.profile_selector.Items.IndexOf("Default")
        if idx >= 0: self.profile_selector.SelectedIndex = idx
        elif self.profile_selector.Items.Count > 0: self.profile_selector.SelectedIndex = 0
        self.load_zone_ui_from_config(self.current_zone)

    def profile_changed(self, sender, e):
        p_name = self.profile_selector.SelectedItem
        if not p_name or p_name not in self.pm.profiles: return
        data = self.pm.profiles[p_name]
        g = data.get("Global", {})
        try:
            self.side_cover.Text = str(g.get("SideCover", 25))
            self.end_offset.Text = str(g.get("EndOffset", 40))
            self.end_spacing.Text = str(g.get("EndSpacing", 150))
            self.mid_spacing.Text = str(g.get("MidSpacing", 250))
            self.beam_width_ui.Text = str(g.get("BeamWidth", 300))
            self.beam_height_ui.Text = str(g.get("BeamHeight", 600))
            
            def set_cb(cb, val):
                if val:
                    i = cb.Items.IndexOf(str(val))
                    if i >= 0: cb.SelectedIndex = i
            
            set_cb(self.bar_type_selector, g.get("BarType"))
            set_cb(self.stirrup_selector, g.get("StirrupType"))
        except: pass
        
        self.zone_configs["End Sections"] = data.get("End Sections", {"T1": 2, "T2": 0, "B1": 2, "B2": 0}).copy()
        self.zone_configs["Middle Section"] = data.get("Middle Section", {"T1": 2, "T2": 0, "B1": 2, "B2": 0}).copy()
        self.load_zone_ui_from_config(self.current_zone)
        self.calculate_all_zones()

    def save_profile_click(self, sender, e):
        from pyrevit.forms import ask_for_string
        name = ask_for_string(prompt="Enter Profile Name:", title="Save Profile")
        if not name: return
        self.update_zone_config_from_ui(self.current_zone)
        data = {
            "End Sections": self.zone_configs["End Sections"],
            "Middle Section": self.zone_configs["Middle Section"],
            "Global": {
                "SideCover": self.side_cover.Text,
                "EndOffset": self.end_offset.Text,
                "EndSpacing": self.end_spacing.Text,
                "MidSpacing": self.mid_spacing.Text,
                "BeamWidth": self.beam_width_ui.Text,
                "BeamHeight": self.beam_height_ui.Text,
                "BarType": str(self.bar_type_selector.SelectedItem),
                "StirrupType": str(self.stirrup_selector.SelectedItem)
            }
        }
        if self.pm.save_profile(name, data):
            if not self.profile_selector.Items.Contains(name): self.profile_selector.Items.Add(name)
            self.profile_selector.SelectedItem = name
            forms.alert("Profile Saved!")
        else: forms.alert("Error saving profile.")

    def zone_input_changed(self, sender, e):
        self.update_zone_config_from_ui(self.current_zone)
        self.calculate_bars(self.current_zone)

    def global_input_changed(self, sender, e):
        try:
            self.beam_w_ft = float(self.beam_width_ui.Text) / 304.8
            self.beam_h_ft = float(self.beam_height_ui.Text) / 304.8
        except: pass
        self.calculate_all_zones()

    def update_zone_config_from_ui(self, zone):
        def _q(cb):
            try: return int(str(cb.SelectedItem))
            except: return 0
        self.zone_configs[zone] = {
            "T1": _q(self.top_L1_qty), "T2": _q(self.top_L2_qty),
            "B1": _q(self.bot_L1_qty), "B2": _q(self.bot_L2_qty)
        }

    def load_zone_ui_from_config(self, zone):
        cfg = self.zone_configs.get(zone, {})
        self.top_L1_qty.SelectedItem = str(cfg.get("T1", 2))
        self.top_L2_qty.SelectedItem = str(cfg.get("T2", 0))
        self.bot_L1_qty.SelectedItem = str(cfg.get("B1", 2))
        self.bot_L2_qty.SelectedItem = str(cfg.get("B2", 0))

    def calculate_all_zones(self):
        for z in ["End Sections", "Middle Section"]: self.calculate_bars(z)

    def calculate_bars(self, zone_to_calc):
        try:
            sb = str(self.bar_type_selector.SelectedItem)
            ss = str(self.stirrup_selector.SelectedItem)
            if not sb: return
            md = next((d[1] for d in self.bar_types_data if d[0] == sb), 0.02)
            sd = next((d[1] for d in self.stirrup_types_data if d[0] == ss), 0.01) if ss else 0.01
            try: cov = float(self.side_cover.Text) / 304.8
            except: cov = 0.025 / 0.3048
            cfg = self.zone_configs[zone_to_calc]
            
            ew = float(self.beam_w_ft) - 2*cov - 2*sd - md
            if ew <= 0: return 
            sx = -float(self.beam_w_ft)/2 + cov + sd + md/2
            nb = []
            def gl(qty, y):
                if qty == 1: nb.append(RebarPoint(0, y, md, sb))
                elif qty > 1:
                    sp = ew / (qty - 1)
                    for i in range(qty): nb.append(RebarPoint(sx + i * sp, y, md, sb))
            yt1 = float(self.beam_h_ft)/2 - cov - sd - md/2
            gl(cfg["T1"], yt1)
            if cfg["T2"] > 0: gl(cfg["T2"], yt1 - md - max(md, 0.082))
            yb1 = -float(self.beam_h_ft)/2 + cov + sd + md/2
            gl(cfg["B1"], yb1)
            if cfg["B2"] > 0: gl(cfg["B2"], yb1 + md + max(md, 0.082))
            self.bars[zone_to_calc] = nb
            if zone_to_calc == self.current_zone: self.draw_ui()
        except: pass

    def setup_canvas(self):
        self.rebar_canvas.Width, self.rebar_canvas.Height = 300.0, 240.0
        aspect = float(self.beam_w_ft) / float(self.beam_h_ft)
        if aspect > (300.0/240.0): self.scale = 300.0 / float(self.beam_w_ft)
        else: self.scale = 240.0 / float(self.beam_h_ft)
            
    def draw_ui(self):
        self.rebar_canvas.Children.Clear()
        self.setup_canvas() # Dynamic Scale
        bw, bh = float(self.beam_w_ft) * self.scale, float(self.beam_h_ft) * self.scale
        cx, cy = 150.0, 120.0
        
        # Main Beam Rect
        rect = Rectangle()
        rect.Width, rect.Height = bw, bh
        rect.Stroke, rect.StrokeThickness = Brushes.Black, 2
        rect.Fill = SolidColorBrush(Color.FromArgb(15, 0, 0, 0))
        Canvas.SetLeft(rect, cx - bw/2)
        Canvas.SetTop(rect, cy - bh/2)
        self.rebar_canvas.Children.Add(rect)
        
        # Stirrup Rect
        try:
            cov = float(self.side_cover.Text) / 304.8
            sw, sh = bw - 2*cov*self.scale, bh - 2*cov*self.scale
            
            # Get current Stirrup Diameter for dynamic thickness
            ss = str(self.stirrup_selector.SelectedItem)
            sd = next((d[1] for d in self.stirrup_types_data if d[0] == ss), 0.01) if ss else 0.01
            # Scale diameter to pixels
            stroke_thk = max(sd * self.scale, 2.0) # Min 2px
            
            if sw > 0 and sh > 0:
                s_rect = Rectangle()
                s_rect.Width, s_rect.Height = sw, sh
                s_rect.Stroke = Brushes.Red
                s_rect.StrokeThickness = stroke_thk
                
                Canvas.SetLeft(s_rect, cx - sw/2)
                Canvas.SetTop(s_rect, cy - sh/2)
                self.rebar_canvas.Children.Add(s_rect)
        except: pass
        
        # Bars
        for rb in self.bars.get(self.current_zone, []):
            dia = max(rb.diameter_ft * self.scale, 4)
            ell = Ellipse()
            ell.Width = ell.Height = dia
            ell.Fill, ell.Stroke, ell.StrokeThickness = Brushes.SteelBlue, Brushes.White, 1
            Canvas.SetLeft(ell, cx + rb.lx * self.scale - dia/2)
            Canvas.SetTop(ell, cy - rb.ly * self.scale - dia/2)
            self.rebar_canvas.Children.Add(ell)

    def switch_zone_click(self, sender, e):
        self.update_zone_config_from_ui(self.current_zone)
        self.current_zone = "Middle Section" if "End" in self.current_zone else "End Sections"
        self.update_zoning_info()
        self.load_zone_ui_from_config(self.current_zone)
        self.draw_ui()

    def update_zoning_info(self):
        self.zone_title.Text = "Editing: " + self.current_zone
        self.switch_zone_btn.Content = "Switch to " + ("End Sections" if "Middle" in self.current_zone else "Middle Section")

    def submit_click(self, sender, e): self.DialogResult = True; self.Close()

# --- XAML ---
xaml_content = """
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="Rebar Profile Manager" Height="900" Width="450" WindowStartupLocation="CenterScreen">
    <Grid Margin="15">
        <Grid.RowDefinitions>
            <RowDefinition Height="Auto"/><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/>
            <RowDefinition Height="Auto"/><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/>
            <RowDefinition Height="Auto"/><RowDefinition Height="*"/><RowDefinition Height="Auto"/>
        </Grid.RowDefinitions>
        
        <TextBlock Grid.Row="0" Text="Beam Rebar Designer" FontSize="18" FontWeight="Bold" Margin="0,0,0,10"/>
        
        <Grid Grid.Row="1" Margin="0,0,0,10">
            <Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions>
            <StackPanel Grid.Column="0"><TextBlock Text="Load Profile:"/><ComboBox x:Name="profile_selector" Margin="0,2,5,0"/></StackPanel>
            <Button x:Name="save_profile_btn" Content="Save As..." Grid.Column="1" Padding="10,0" VerticalAlignment="Bottom" Height="22" Margin="0,0,0,2"/>
        </Grid>

        <!-- Beam Dimensions Input -->
        <GroupBox Grid.Row="2" Header="Design Beam Size (mm)" Margin="0,0,0,10">
            <Grid Margin="5">
                <Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="*"/></Grid.ColumnDefinitions>
                <StackPanel Margin="0,0,5,0"><TextBlock Text="Width (b):"/><TextBox x:Name="beam_width_ui" Text="300"/></StackPanel>
                <StackPanel Grid.Column="1" Margin="5,0,0,0"><TextBlock Text="Height (h):"/><TextBox x:Name="beam_height_ui" Text="600"/></StackPanel>
            </Grid>
        </GroupBox>
        
        <Border Grid.Row="3" Background="#FAFAFA" BorderBrush="#DDD" BorderThickness="1" CornerRadius="5" Padding="10">
            <StackPanel>
                <Grid Margin="0,0,0,5"><TextBlock x:Name="zone_title" FontWeight="Bold"/><Button x:Name="switch_zone_btn" HorizontalAlignment="Right" Click="switch_zone_click" Padding="8,2" FontSize="10"/></Grid>
                <Canvas x:Name="rebar_canvas" Width="300" Height="240" HorizontalAlignment="Center"/>
            </StackPanel>
        </Border>

        <Grid Grid.Row="4" Margin="0,15,0,5">
            <Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="*"/></Grid.ColumnDefinitions>
            <StackPanel Grid.Column="0" Margin="0,0,5,0"><TextBlock Text="Main Bar Type:"/><ComboBox x:Name="bar_type_selector"/></StackPanel>
            <StackPanel Grid.Column="1" Margin="5,0,0,0"><TextBlock Text="Stirrup Type:"/><ComboBox x:Name="stirrup_selector"/></StackPanel>
        </Grid>
        
        <Grid Grid.Row="5" Margin="0,0,0,15">
            <Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="*"/></Grid.ColumnDefinitions>
            <StackPanel Grid.Column="0" Margin="0,0,5,0"><TextBlock Text="Side Cover (mm):"/><TextBox x:Name="side_cover" Text="25"/></StackPanel>
            <StackPanel Grid.Column="1" Margin="5,0,0,0"><TextBlock Text="End Offset (mm):"/><TextBox x:Name="end_offset" Text="40"/></StackPanel>
        </Grid>

        <GroupBox Grid.Row="6" Header="Bar Quantities" Margin="0,0,0,10">
            <Grid Margin="5">
                <Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="*"/></Grid.ColumnDefinitions>
                <Grid.RowDefinitions>
                    <RowDefinition Height="Auto"/>
                    <RowDefinition Height="Auto"/>
                    <RowDefinition Height="10"/>
                    <RowDefinition Height="Auto"/>
                    <RowDefinition Height="Auto"/>
                </Grid.RowDefinitions>
                <TextBlock Grid.Row="0" Text="Top Outer (L1):" VerticalAlignment="Center"/>
                <ComboBox x:Name="top_L1_qty" Grid.Row="0" Grid.Column="1" Margin="0,2"/>
                
                <TextBlock Grid.Row="1" Text="Top Inner (L2):" VerticalAlignment="Center"/>
                <ComboBox x:Name="top_L2_qty" Grid.Row="1" Grid.Column="1" Margin="0,2"/>
                
                <TextBlock Grid.Row="3" Text="Bot Outer (L1):" VerticalAlignment="Center"/>
                <ComboBox x:Name="bot_L1_qty" Grid.Row="3" Grid.Column="1" Margin="0,2"/>
                
                <TextBlock Grid.Row="4" Text="Bot Inner (L2):" VerticalAlignment="Center"/>
                <ComboBox x:Name="bot_L2_qty" Grid.Row="4" Grid.Column="1" Margin="0,2"/>
            </Grid>
        </GroupBox>

        <Grid Grid.Row="7" VerticalAlignment="Top">
            <Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="*"/></Grid.ColumnDefinitions>
            <StackPanel Grid.Column="0" Margin="0,0,5,0"><TextBlock Text="End Spacing:"/><TextBox x:Name="end_spacing" Text="150"/></StackPanel>
            <StackPanel Grid.Column="1" Margin="5,0,0,0"><TextBlock Text="Mid Spacing:"/><TextBox x:Name="mid_spacing" Text="250"/></StackPanel>
        </Grid>

        <Button Grid.Row="8" Content="Select Beam &amp; Apply" Height="45" Click="submit_click" Background="#007ACC" Foreground="White" FontWeight="Bold" Margin="0,15,0,0"/>
    </Grid>
</Window>
"""

def create_rebar():
    doc = revit.doc
    try:
        # Check and ensure 6mm and 8mm exist
        def ensure_bar_type(name, dia_mm):
            bts = DB.FilteredElementCollector(doc).OfClass(DB.Structure.RebarBarType).ToElements()
            for b in bts:
                # Safe Name Access
                bn = b.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString()
                if not bn:
                    try: bn = b.Name
                    except: pass
                if bn == name or bn == str(name) + "mm": return b
            
            # Create if missing (Duplicate first one)
            if bts:
                with revit.Transaction("Create Rebar Type " + name):
                    new_t = bts[0].Duplicate(name)
                    new_t.get_Parameter(DB.BuiltInParameter.REBAR_BAR_DIAMETER).Set(dia_mm / 304.8)
                    return new_t
            return None

        # Auto-create common sizes if missing
        ensure_bar_type("6mm", 6)
        ensure_bar_type("8mm", 8)
        ensure_bar_type("10mm", 10)
        ensure_bar_type("12mm", 12)

        bts = DB.FilteredElementCollector(doc).OfClass(DB.Structure.RebarBarType).ToElements()
        bt_data = []
        for b in bts:
            n = b.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString() or b.Name
            d = 0.04
            try: d = b.get_Parameter(DB.BuiltInParameter.REBAR_BAR_DIAMETER).AsDouble()
            except: pass
            bt_data.append((n, d))
        # Sort by Name for better UI
        bt_data.sort(key=lambda x: x[0])

        if not bt_data: return forms.alert("No Rebar Types")

        def find_t(name):
            n_ = str(name)
            for t in bts:
                nt = t.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString() or t.Name
                if nt == n_: return t
            return None

        pm = ProfileManager()
        temp = os.path.join(os.environ['TEMP'], 'beamrebar_v5.xaml')
        with open(temp, 'w') as f: f.write(xaml_content)
        
        win = ParametricRebarWindow(temp) 
        win.setup_data(bt_data, bt_data, pm)
        if not win.show_dialog(): return

        # PICK BEAMS
        from Autodesk.Revit.UI.Selection import ObjectType
        filt = BeamSelectionFilter()
        beams = []
        try:
            refs = revit.uidoc.Selection.PickObjects(ObjectType.Element, filt, "Select Beams")
            for r in refs: beams.append(doc.GetElement(r))
        except: return
        if not beams: return forms.alert("No Beams selected.")

        # VALIDATION & PARAMS
        def get_beam_dims_geometric(b):
            # Returns: width, height, center_y, center_z
            # Attempt 1: Geometric Extraction
            try:
                opt = DB.Options()
                opt.ComputeReferences = True
                opt.DetailLevel = DB.ViewDetailLevel.Fine
                geom = b.get_Geometry(opt)
                
                def get_solids(g_elem):
                    sols = []
                    for g in g_elem:
                        if isinstance(g, DB.Solid) and g.Volume > 0:
                            sols.append(g)
                        elif isinstance(g, DB.GeometryInstance):
                            sols.extend(get_solids(g.GetInstanceGeometry()))
                    return sols

                all_solids = get_solids(geom)
                if all_solids:
                    best_solid = max(all_solids, key=lambda s: s.Volume)
                    trans = b.GetTransform()
                    inv_trans = trans.Inverse
                    
                    min_y, max_y = 99999.0, -99999.0
                    min_z, max_z = 99999.0, -99999.0
                    
                    for edge in best_solid.Edges:
                         pts = edge.Tessellate()
                         for p in pts:
                             local_p = inv_trans.OfPoint(p)
                             if local_p.Y < min_y: min_y = local_p.Y
                             if local_p.Y > max_y: max_y = local_p.Y
                             if local_p.Z < min_z: min_z = local_p.Z
                             if local_p.Z > max_z: max_z = local_p.Z
                    
                    w = max_y - min_y
                    h = max_z - min_z
                    cy = (min_y + max_y) / 2.0
                    cz = (min_z + max_z) / 2.0
                    
                    # Rounding
                    w = round(w * 304.8, 1) / 304.8
                    h = round(h * 304.8, 1) / 304.8
                    
                    if w > 0 and h > 0:
                        return w, h, cy, cz
            except Exception as e: 
                print("Geometric error: " + str(e))

            # Attempt 2: Fallback (Assume Centered)
            s = b.Symbol
            wp = s.LookupParameter("b") or s.LookupParameter("Width") or s.LookupParameter("Width (b)")
            hp = s.LookupParameter("h") or s.LookupParameter("Height") or s.LookupParameter("Height (h)")
            w_val = wp.AsDouble() if wp else None
            h_val = hp.AsDouble() if hp else None
            return w_val, h_val, 0.0, 0.0

        ref_w, ref_h, _, _ = get_beam_dims_geometric(beams[0])
        
        if ref_w is None: return forms.alert("Could not get beam dimensions. Ensure the family is rectangular.")
        for b in beams:
            w, h, _, _ = get_beam_dims_geometric(b)
            if not w or abs(w-ref_w)>0.001 or abs(h-ref_h)>0.001: return forms.alert("Selected beams must have identical sizes!")

        es, ms = float(win.end_spacing.Text)/304.8, float(win.mid_spacing.Text)/304.8
        cov, off = float(win.side_cover.Text)/304.8, float(win.end_offset.Text)/304.8
        st_t, bt_t = find_t(win.stirrup_selector.SelectedItem), find_t(win.bar_type_selector.SelectedItem)
        if not st_t or not bt_t: return forms.alert("Selected Rebar Types not found")

        # GENERATION
        def get_lbs(zone, bw, bh):
             cfg = win.zone_configs[zone]
             md = bt_t.get_Parameter(DB.BuiltInParameter.REBAR_BAR_DIAMETER).AsDouble()
             sd = st_t.get_Parameter(DB.BuiltInParameter.REBAR_BAR_DIAMETER).AsDouble()
             ew = bw - 2.0*cov - 2.0*sd - md
             if ew <= 0: return []
             sx = -bw/2.0 + cov + sd + md/2.0
             lbs = []
             b_name_str = str(win.bar_type_selector.SelectedItem)
             def gl(q, y):
                 if q == 1: lbs.append(RebarPoint(0, y, md, b_name_str))
                 elif q > 1:
                     s = ew / (q-1)
                     for i in range(q): lbs.append(RebarPoint(sx + i*s, y, md, b_name_str))
             yt1 = bh/2.0 - cov - sd - md/2.0
             gl(cfg["T1"], yt1)
             if cfg["T2"] > 0: gl(cfg["T2"], yt1 - md - max(md, 0.082))
             yb1 = -bh/2.0 + cov + sd + md/2.0
             gl(cfg["B1"], yb1)
             if cfg["B2"] > 0: gl(cfg["B2"], yb1 + md + max(md, 0.082))
             return lbs

        debug_log = []
        def log(msg): debug_log.append(msg)

        with revit.Transaction("Batch Beam Rebar"):
            view = doc.ActiveView
            is_3d = isinstance(view, DB.View3D)
            
            for b_idx, b in enumerate(beams):
                log("Processing Beam {}: ID {}".format(b_idx, b.Id))
                
                # Recalculate geometry/center for this specific instance
                dims = get_beam_dims_geometric(b)
                bw, bh, cy, cz = dims
                log("  Dims: w={}, h={}, cy={}, cz={}".format(bw, bh, cy, cz))
                
                if not bw: 
                    log("  SKIP: Could not determine dimensions")
                    continue

                c = b.Location.Curve
                p0, p1 = c.GetEndPoint(0), c.GetEndPoint(1)
                trans = b.GetTransform()
                bx, bz = trans.BasisX, trans.BasisZ
                lx0, lx1 = (p0-trans.Origin).DotProduct(bx), (p1-trans.Origin).DotProduct(bx)
                if lx0 > lx1: lx0, lx1 = lx1, lx0
                zs = (lx1-lx0)/3.0

                def set_vis(r_elem):
                    if r_elem:
                        try:
                            r_elem.SetUnobscuredInView(view, True)
                            if is_3d: r_elem.SetSolidInView(view, True)
                        except: pass

                def mks(sx, ex, sp):
                    lw, lh = bw-2*cov, bh-2*cov
                    # Shift points by cy, cz to align with beam center
                    pts = [DB.XYZ(sx, cy-lw/2, cz-lh/2), 
                           DB.XYZ(sx, cy+lw/2, cz-lh/2), 
                           DB.XYZ(sx, cy+lw/2, cz+lh/2), 
                           DB.XYZ(sx, cy-lw/2, cz+lh/2)]
                    curv = List[DB.Curve]()
                    
                    # Create Loop
                    try:
                        for i in range(4): 
                            p_start = trans.OfPoint(pts[i])
                            p_end = trans.OfPoint(pts[(i+1)%4])
                            curv.Add(DB.Line.CreateBound(p_start, p_end))
                        
                        r = DB.Structure.Rebar.CreateFromCurves(doc, DB.Structure.RebarStyle.StirrupTie, st_t, None, None, b, bx, curv, DB.Structure.RebarHookOrientation.Right, DB.Structure.RebarHookOrientation.Right, True, True)
                        
                        if r:
                            zl = ex-sx
                            qty = int(math.floor(zl/sp)) + 1
                            if qty > 1: r.GetShapeDrivenAccessor().SetLayoutAsNumberWithSpacing(qty, sp, True, True, True)
                            set_vis(r)
                        else:
                            log("  FAIL: Rebar.CreateFromCurves returned None (Stirrup)")
                    except Exception as e:
                        log("  ERROR Stirrup: " + str(e))

                # Define 3 physical zones
                # 1. Start Zone (End Sections)
                # 2. Middle Zone (Middle Section)
                # 3. End Zone (End Sections)
                
                physical_zones = [
                    {"name": "End Sections",   "sx": lx0+off,   "ex": lx0+zs},
                    {"name": "Middle Section", "sx": lx0+zs,    "ex": lx0+2*zs},
                    {"name": "End Sections",   "sx": lx0+2*zs,  "ex": lx1-off}
                ]

                # Stirrups (Already correct, but could unify if desired. Keeping as is for safety)
                mks(lx0+off, lx0+zs, es)
                mks(lx0+zs, lx0+2*zs, ms)
                mks(lx0+2*zs, lx1-off, es)

                # Main Bars
                for pz in physical_zones:
                    z_name = pz["name"]
                    sx = pz["sx"]
                    ex = pz["ex"]
                    
                    if ex <= sx: continue # Skip invalid geometry

                    for rb in get_lbs(z_name, bw, bh):
                        try:
                            lc = List[DB.Curve]()
                            p1_loc = DB.XYZ(sx, rb.lx + cy, rb.ly + cz)
                            p2_loc = DB.XYZ(ex, rb.lx + cy, rb.ly + cz)
                            
                            p1_glob = trans.OfPoint(p1_loc)
                            p2_glob = trans.OfPoint(p2_loc)
                            
                            lc.Add(DB.Line.CreateBound(p1_glob, p2_glob))
                            r = DB.Structure.Rebar.CreateFromCurves(doc, DB.Structure.RebarStyle.Standard, bt_t, None, None, b, bz, lc, DB.Structure.RebarHookOrientation.Right, DB.Structure.RebarHookOrientation.Right, True, True)
                            set_vis(r)
                            if not r: log("  FAIL: Main Bar create returned None")
                        except Exception as e:
                            log("  ERROR MainBar: " + str(e))
            
            if len(debug_log) > 0:
                forms.alert("\n".join(debug_log), title="Debug Log")
            else:
                forms.alert("Complete for {} beams!".format(len(beams)))



    except Exception: forms.alert(traceback.format_exc())
    finally:
        if os.path.exists(temp): os.remove(temp)

if __name__ == '__main__': create_rebar()
