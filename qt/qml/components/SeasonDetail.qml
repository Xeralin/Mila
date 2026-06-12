pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

Item {
    id: detail

    property var season: ({})
    signal back()

    property string key: season.key !== undefined ? season.key : ""
    property bool active: downloader.active_key === detail.key
    property var variants: ({ throwback: false, hm: false })
    property bool prefix_tb: false
    property bool prefix_hm: false
    property bool liberator_on: true
    property bool hm_on: true

    Component.onCompleted: detail.refresh_variants()

    function refresh_variants() {
        variants = tools.installed_variants(detail.key)
        prefix_tb = tools.prefix_exists(detail.key, false)
        prefix_hm = tools.prefix_exists(detail.key, true)
    }

    function add_to_steam() {
        steamPanel.steam_running = downloader.is_steam_running()
        if (!steamPanel.steam_running) {
            downloader.refresh_protons()
            if (downloader.protons.length === 0) {
                toast.show_error("No Proton found")
                steamPanel.close()
                return
            }
        }
        steamPanel.open()
    }

    Rectangle { anchors.fill: parent; color: Theme.background }

    Item {
        id: hero
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: Math.round(detail.height * 0.46)

        Image {
            anchors.fill: parent
            visible: season.has_splash === true
            source: season.has_splash === true ? season.splash : ""
            fillMode: Image.PreserveAspectCrop
            asynchronous: true
        }

        Rectangle {
            anchors.fill: parent
            visible: season.has_splash !== true
            gradient: Gradient {
                GradientStop { position: 0.0; color: Theme.gradient_top }
                GradientStop { position: 1.0; color: Theme.gradient_bottom }
            }
        }

        Rectangle {
            anchors.fill: parent
            gradient: Gradient {
                GradientStop { position: 0.0; color: Theme.hero_shade_top }
                GradientStop { position: 0.55; color: Theme.hero_shade_clear }
                GradientStop { position: 1.0; color: Theme.hero_shade_bottom }
            }
        }

        Column {
            anchors.left: parent.left
            anchors.leftMargin: 44
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 22
            spacing: 4
            Label {
                text: season.code !== undefined ? season.code : ""
                color: Theme.text_soft
                font.pixelSize: 20
                font.bold: true
                font.letterSpacing: 3
            }
            Label {
                text: season.name !== undefined ? season.name : ""
                color: Theme.text_primary
                font.pixelSize: 46
                font.bold: true
                style: Text.Raised
                styleColor: Theme.text_shadow
            }
        }
    }

    MilaButton {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.margins: 16
        width: 38
        height: 76
        neighbors: "none"
        leftPadding: 0
        rightPadding: 0
        font.pixelSize: 28
        font.letterSpacing: 0
        text: "❮"
        onClicked: detail.back()
    }

    ColumnLayout {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: hero.bottom
        anchors.bottom: parent.bottom
        anchors.leftMargin: 44
        anchors.rightMargin: 44
        anchors.topMargin: 28
        anchors.bottomMargin: 28
        spacing: 22

        RowLayout {
            Layout.fillWidth: true
            spacing: 28
            Label {
                visible: !!season.size_gb
                text: (season.size_gb !== undefined ? season.size_gb : "") + " GB"
                color: Theme.text_secondary
                font.pixelSize: 18
            }
            Item { Layout.fillWidth: true }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 16
            MilaButton {
                readonly property bool is_cancel: detail.active && downloader.running
                readonly property bool installed: detail.variants.throwback === true || detail.variants.hm === true

                Layout.preferredWidth: 200
                variant: is_cancel ? "ghost" : "primary"
                destructive: is_cancel
                enabled: !downloader.running || detail.active
                text: is_cancel ? "Cancel" : (installed ? "Download again" : "Download")
                onClicked: {
                    if (is_cancel)
                        downloader.cancel()
                    else
                        downloader.start(detail.key,
                                         season.liberator === true && detail.liberator_on,
                                         season.heated_metal === true && detail.hm_on)
                }
            }
            Label {
                visible: detail.active && (downloader.state === "done" || downloader.state === "failed")
                text: downloader.state === "done" ? "Installed" : "Failed — see log"
                color: downloader.state === "done" ? Theme.success : Theme.error
                font.pixelSize: 16
                font.bold: true
            }
            MilaButton {
                visible: detail.active && downloader.state === "done"
                enabled: !downloader.running
                text: "Add to Steam"
                onClicked: detail.add_to_steam()
            }
            MilaProgressBar {
                Layout.fillWidth: true
                from: 0
                to: 100
                value: downloader.progress
                indeterminate: downloader.state === "applying"
                visible: detail.active && downloader.running
            }
            Label {
                color: Theme.text_primary
                visible: detail.active && downloader.running && downloader.state !== "applying"
                text: Math.round(downloader.progress) + "%"
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 6
            visible: detail.variants.throwback === true || detail.variants.hm === true

            Repeater {
                model: {
                    const rows = []
                    if (detail.variants.throwback === true)
                        rows.push({ label: "Throwback", is_hm: false, shears: true, prefix: detail.prefix_tb })
                    if (detail.variants.hm === true)
                        rows.push({ label: "Heated Metal", is_hm: true, shears: false, prefix: detail.prefix_hm })
                    return rows
                }
                delegate: RowLayout {
                    id: variantRow
                    required property var modelData

                    Layout.fillWidth: true
                    spacing: 8
                    MilaButton {
                        text: "Verify"
                        enabled: !downloader.running && tools.busy === ""
                        onClicked: downloader.verify(detail.key, variantRow.modelData.is_hm)
                    }
                    MilaButton {
                        visible: variantRow.modelData.shears
                        text: "Shears"
                        enabled: tools.busy === ""
                        onClicked: {
                            shearsPanel.payload = null
                            shearsPanel.pending = null
                            shearsPanel.open()
                            tools.scan_shears(detail.key)
                        }
                    }
                    MilaButton {
                        visible: variantRow.modelData.prefix
                        variant: "ghost"
                        destructive: true
                        text: "Delete prefix"
                        enabled: tools.busy === ""
                        onClicked: {
                            prefixDialog.is_hm = variantRow.modelData.is_hm
                            prefixDialog.open()
                        }
                    }
                    Item { Layout.fillWidth: true }
                }
            }
        }

        LogPanel {
            id: logPanel
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: detail.active && downloader.state !== "idle"
            Component.onCompleted: {
                if (detail.active)
                    logPanel.text = downloader.log_history()
            }
        }

        Item {
            Layout.fillHeight: true
            visible: !(detail.active && downloader.state !== "idle")
        }

        GridLayout {
            columns: 2
            columnSpacing: 16
            rowSpacing: 8
            Layout.fillWidth: false
            visible: season.liberator === true || season.heated_metal === true

            Label {
                visible: season.liberator === true
                text: "Liberator"
                color: Theme.text_secondary
                font.pixelSize: Theme.font_body
                Layout.alignment: Qt.AlignVCenter
            }
            MilaOptionControl {
                visible: season.liberator === true
                neighbors: "vertical"
                enabled: !downloader.running
                options: [{ label: "Off", value: false }, { label: "On", value: true }]
                current_value: detail.liberator_on
                onPicked: function(value) {
                    detail.liberator_on = value
                    if (value)
                        detail.hm_on = false
                }
            }
            Label {
                visible: season.heated_metal === true
                text: "Heated Metal"
                color: Theme.text_secondary
                font.pixelSize: Theme.font_body
                Layout.alignment: Qt.AlignVCenter
            }
            MilaOptionControl {
                visible: season.heated_metal === true
                neighbors: "vertical"
                enabled: !downloader.running
                options: [{ label: "Off", value: false }, { label: "On", value: true }]
                current_value: detail.hm_on
                onPicked: function(value) {
                    detail.hm_on = value
                    if (value)
                        detail.liberator_on = false
                }
            }
        }
    }

    SidePanel {
        id: steamPanel
        title: "Add to Steam"

        property bool steam_running: false

        Column {
            width: parent.width
            spacing: 16
            visible: steamPanel.steam_running

            Label {
                width: parent.width
                text: "Close Steam to apply"
                color: Theme.warning
                font.pixelSize: Theme.font_body
                wrapMode: Text.Wrap
            }

            MilaButton {
                text: "Retry"
                onClicked: detail.add_to_steam()
            }
        }

        Column {
            width: parent.width
            spacing: 12
            visible: !steamPanel.steam_running

            Label {
                text: "Pick a Proton version"
                color: Theme.text_secondary
                font.pixelSize: Theme.font_body
            }

            Column {
                width: parent.width
                spacing: 2

                Repeater {
                    model: downloader.protons
                    delegate: Rectangle {
                        id: protonEntry
                        required property var modelData

                        width: parent ? parent.width : 0
                        height: Theme.control_height
                        radius: Theme.radius_small
                        color: protonHover.hovered ? Theme.hover : "transparent"
                        Behavior on color { ColorAnimation { duration: 150 } }

                        Label {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            anchors.verticalCenter: parent.verticalCenter
                            text: protonEntry.modelData.display
                            color: Theme.text_primary
                            font.pixelSize: Theme.font_body
                            elide: Text.ElideRight
                        }

                        HoverHandler {
                            id: protonHover
                            cursorShape: Qt.PointingHandCursor
                        }
                        TapHandler {
                            onTapped: {
                                steamPanel.close()
                                downloader.steam_setup(protonEntry.modelData.index)
                            }
                        }
                    }
                }
            }
        }
    }

    SidePanel {
        id: shearsPanel
        title: "Shears"

        property var payload: null
        property var pending: null

        function warning_text() {
            if (pending === null)
                return ""
            if (pending.kind === "videos")
                return "This permanently deletes the video files"
            if (pending.kind === "events")
                return "This permanently deletes event forge files"
            const quality = pending.label.replace("Cut to ", "").replace(" textures", "")
            return "This permanently deletes all textures above " + quality
        }

        MilaBusyIndicator {
            visible: shearsPanel.payload === null
            anchors.horizontalCenter: parent.horizontalCenter
        }

        Column {
            width: parent.width
            spacing: 16
            visible: shearsPanel.payload !== null && shearsPanel.pending === null

            Label {
                text: shearsPanel.payload !== null ? shearsPanel.payload.total + " total" : ""
                color: Theme.text_primary
                font.pixelSize: 18
                font.bold: true
            }

            Column {
                width: parent.width

                Repeater {
                    id: shearsRows
                    model: shearsPanel.payload !== null ? shearsPanel.payload.rows : []
                    delegate: Item {
                        id: shearsRow
                        required property var modelData
                        required property int index

                        width: parent ? parent.width : 0
                        height: 36

                        Label {
                            anchors.left: parent.left
                            anchors.verticalCenter: parent.verticalCenter
                            text: shearsRow.modelData.label
                            color: Theme.text_secondary
                            font.pixelSize: Theme.font_body
                        }
                        Label {
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            text: shearsRow.modelData.size
                            color: Theme.text_primary
                            font.family: "monospace"
                            font.pixelSize: Theme.font_body
                        }
                        Rectangle {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.bottom: parent.bottom
                            height: 1
                            color: Theme.hairline
                            visible: shearsRow.index < shearsRows.count - 1
                        }
                    }
                }
            }

            Label {
                text: "Free up space"
                color: Theme.text_secondary
                font.pixelSize: Theme.font_body
                font.bold: true
            }

            Label {
                visible: shearsPanel.payload !== null && shearsPanel.payload.actions.length === 0
                text: "There's nothing to cut"
                color: Theme.text_secondary
                font.pixelSize: Theme.font_body
            }

            Column {
                width: parent.width
                spacing: 8

                Repeater {
                    model: shearsPanel.payload !== null ? shearsPanel.payload.actions : []
                    delegate: MilaButton {
                        id: shearsAction
                        required property var modelData
                        neighbors: "vertical"

                        width: parent ? parent.width : 0
                        text: shearsAction.modelData.label
                        enabled: tools.busy === ""
                        onClicked: shearsPanel.pending = shearsAction.modelData
                    }
                }
            }
        }

        Column {
            width: parent.width
            spacing: 16
            visible: shearsPanel.pending !== null

            Label {
                width: parent.width
                text: shearsPanel.warning_text()
                color: Theme.text_primary
                font.pixelSize: Theme.font_body
                wrapMode: Text.Wrap
            }

            Row {
                spacing: 12

                MilaButton {
                    text: "Continue"
                    variant: "primary"
                    destructive: true
                    enabled: tools.busy === ""
                    onClicked: tools.cut_shears(shearsPanel.payload.key, shearsPanel.pending.kind,
                                                shearsPanel.pending.level)
                }
                MilaButton {
                    text: "Back"
                    variant: "ghost"
                    enabled: tools.busy === ""
                    onClicked: shearsPanel.pending = null
                }
                MilaBusyIndicator {
                    width: Theme.control_height
                    height: Theme.control_height
                    visible: tools.busy === "cut"
                    running: visible
                }
            }
        }
    }

    MilaDialog {
        id: prefixDialog
        anchors.centerIn: Overlay.overlay
        modal: true
        title: "Delete prefix"

        property bool is_hm: false

        Label { text: "This permanently deletes the Proton prefix" }

        footer: MilaDialogButtonBox {
            MilaButton {
                text: "Continue"
                variant: "primary"
                destructive: true
                DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
            }
            MilaButton {
                text: "Cancel"
                variant: "ghost"
                DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
            }
        }

        onAccepted: tools.delete_prefix(detail.key, prefixDialog.is_hm)
    }

    Toast {
        id: toast
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 28
    }

    Connections {
        target: downloader
        function onLog_line(line) {
            if (detail.active)
                logPanel.append(line)
        }
        function onSteam_setup_done(ok, message) {
            if (!detail.active)
                return
            if (ok)
                toast.show(message)
            else
                toast.show_error(message)
        }
        function onFinished() {
            detail.refresh_variants()
        }
    }

    Connections {
        target: tools
        function onError(message) {
            toast.show_error(message)
        }
        function onShears_scanned(data) {
            if (data.key === detail.key)
                shearsPanel.payload = data
        }
        function onShears_done(ok, message) {
            if (ok)
                toast.show(message)
            else
                toast.show_error(message)
            if (shearsPanel.visible) {
                shearsPanel.pending = null
                shearsPanel.payload = null
                tools.scan_shears(detail.key)
            }
        }
        function onPrefix_deleted(ok, message) {
            if (ok)
                toast.show(message)
            else
                toast.show_error(message)
            detail.refresh_variants()
        }
    }
}
