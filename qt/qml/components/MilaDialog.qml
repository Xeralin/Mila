import QtQuick
import QtQuick.Controls.Basic
import ".."

Dialog {
    id: control

    padding: 20

    Overlay.modal: Rectangle {
        color: Theme.dialog_scrim
    }

    background: Rectangle {
        color: Theme.surface
        radius: Theme.radius
        border.width: 1
        border.color: Theme.hairline_strong
    }

    header: Label {
        text: control.title
        visible: control.title.length > 0
        elide: Text.ElideRight
        color: Theme.text_primary
        font.pixelSize: 18
        font.weight: Font.Bold
        font.capitalization: Font.AllUppercase
        font.letterSpacing: 1.5
        leftPadding: 20
        rightPadding: 20
        topPadding: 20
    }

    enter: Transition {
        NumberAnimation { property: "opacity"; from: 0.0; to: 1.0; duration: 150; easing.type: Easing.OutCubic }
        NumberAnimation { property: "scale"; from: 0.96; to: 1.0; duration: 150; easing.type: Easing.OutCubic }
    }

    exit: Transition {
        NumberAnimation { property: "opacity"; from: 1.0; to: 0.0; duration: 150; easing.type: Easing.InCubic }
        NumberAnimation { property: "scale"; from: 1.0; to: 0.96; duration: 150; easing.type: Easing.InCubic }
    }
}
